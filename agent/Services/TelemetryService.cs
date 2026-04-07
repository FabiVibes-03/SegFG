using System.Diagnostics;
using System.Management;
using System.Net;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using TabletMonitor.Models;

namespace TabletMonitor.Services;

/// <summary>
/// Recopila telemetría del sistema: batería, CPU, RAM, disco, red WiFi y GPS.
/// Usa WMI (Windows Management Instrumentation) — funciona en todas las versiones de Windows.
/// </summary>
[SupportedOSPlatform("windows")]
public class TelemetryService
{
    private readonly ILogger<TelemetryService> _logger;
    private readonly PerformanceCounter _cpuCounter;

    public TelemetryService(ILogger<TelemetryService> logger)
    {
        _logger = logger;
        // El PerformanceCounter necesita una lectura previa antes de dar valores válidos
        _cpuCounter = new PerformanceCounter("Processor", "% Processor Time", "_Total");
        _cpuCounter.NextValue(); // primera lectura descartada
    }

    public async Task<HeartbeatPayload> CollectAsync()
    {
        var payload = new HeartbeatPayload();

        // Recopilar en paralelo para no bloquear
        await Task.WhenAll(
            Task.Run(() => CollectBattery(payload)),
            Task.Run(() => CollectHardware(payload)),
            Task.Run(() => CollectNetwork(payload)),
            Task.Run(() => CollectSystem(payload)),
            CollectGpsAsync(payload)
        );

        return payload;
    }

    // ────────────────────────────────────────────────
    // Batería
    // ────────────────────────────────────────────────

    private void CollectBattery(HeartbeatPayload p)
    {
        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_Battery");
            foreach (ManagementObject obj in searcher.Get())
            {
                // EstimatedChargeRemaining: 0-100
                if (obj["EstimatedChargeRemaining"] != null)
                    p.BatteryLevel = Convert.ToInt32(obj["EstimatedChargeRemaining"]);

                // BatteryStatus: 2 = cargando, 1 = descargando, 3 = carga completa
                var status = Convert.ToUInt16(obj["BatteryStatus"]);
                p.BatteryCharging = status == 2 || status == 3;
                p.BatteryStatus   = status switch
                {
                    1 => "Discharging",
                    2 => "Charging",
                    3 => "Full",
                    4 => "Low",
                    5 => "Critical",
                    _ => "Unknown"
                };
                break; // Solo primera batería
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("No se pudo leer batería: {msg}", ex.Message);
            // Tablets de escritorio o sin batería — no es error crítico
        }
    }

    // ────────────────────────────────────────────────
    // CPU, RAM, Disco
    // ────────────────────────────────────────────────

    private void CollectHardware(HeartbeatPayload p)
    {
        try
        {
            // CPU — PerformanceCounter es más preciso que WMI para uso en tiempo real
            p.CpuUsage = Math.Round(_cpuCounter.NextValue(), 1);
        }
        catch (Exception ex)
        {
            _logger.LogDebug("CPU counter error: {msg}", ex.Message);
        }

        try
        {
            // RAM vía WMI
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_OperatingSystem");
            foreach (ManagementObject obj in searcher.Get())
            {
                var totalKb = Convert.ToInt64(obj["TotalVisibleMemorySize"]);
                var freeKb  = Convert.ToInt64(obj["FreePhysicalMemory"]);
                p.RamTotalMb = (int)(totalKb / 1024);
                p.RamUsedMb  = (int)((totalKb - freeKb) / 1024);
                break;
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("RAM WMI error: {msg}", ex.Message);
        }

        try
        {
            // Disco — unidad del sistema (C:\)
            var drive = DriveInfo.GetDrives().FirstOrDefault(d => d.IsReady && d.Name == "C:\\");
            if (drive != null)
            {
                p.DiskTotalGb = Math.Round(drive.TotalSize / 1_073_741_824.0, 1);
                p.DiskFreeGb  = Math.Round(drive.AvailableFreeSpace / 1_073_741_824.0, 1);
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("Disk error: {msg}", ex.Message);
        }
    }

    // ────────────────────────────────────────────────
    // Red — IP, MAC, WiFi SSID
    // ────────────────────────────────────────────────

    private void CollectNetwork(HeartbeatPayload p)
    {
        try
        {
            // IP activa (la que tiene gateway — ignora loopback y virtuales)
            foreach (var ni in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (ni.OperationalStatus != OperationalStatus.Up) continue;
                if (ni.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;

                var props = ni.GetIPProperties();
                if (!props.GatewayAddresses.Any()) continue;

                // MAC
                p.MacAddress = string.Join(":", ni.GetPhysicalAddress().GetAddressBytes()
                    .Select(b => b.ToString("X2")));

                // IP v4
                var ipv4 = props.UnicastAddresses
                    .FirstOrDefault(a => a.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork);
                if (ipv4 != null)
                    p.IpAddress = ipv4.Address.ToString();

                break;
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("Network error: {msg}", ex.Message);
        }

        try
        {
            // SSID WiFi — via netsh (más confiable que WMI para WiFi)
            var result = RunCommand("netsh", "wlan show interfaces");
            var ssidLine = result.Split('\n')
                .FirstOrDefault(l => l.TrimStart().StartsWith("SSID") && !l.Contains("BSSID"));

            if (ssidLine != null)
            {
                var parts = ssidLine.Split(':');
                if (parts.Length > 1)
                    p.Ssid = parts[1].Trim();
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug("WiFi SSID error: {msg}", ex.Message);
        }
    }

    // ────────────────────────────────────────────────
    // Sistema — OS, uptime, usuario, pantalla bloqueada
    // ────────────────────────────────────────────────

    private void CollectSystem(HeartbeatPayload p)
    {
        try
        {
            p.OsVersion  = Environment.OSVersion.VersionString;
            p.ActiveUser = Environment.UserName;

            // Uptime en segundos
            p.UptimeSeconds = (int)(Environment.TickCount64 / 1000);

            // Pantalla bloqueada — verifica si el proceso winlogon tiene el escritorio bloqueado
            p.ScreenLocked = IsScreenLocked();
        }
        catch (Exception ex)
        {
            _logger.LogDebug("System info error: {msg}", ex.Message);
        }
    }

    // ────────────────────────────────────────────────
    // GPS — Windows.Devices.Geolocation
    // ────────────────────────────────────────────────

    private async Task CollectGpsAsync(HeartbeatPayload p)
    {
        try
        {
            // Solo intentar si la tablet tiene GPS
            // Windows.Devices.Geolocation requiere que el servicio de ubicación esté habilitado
            var locator = new Windows.Devices.Geolocation.Geolocator
            {
                DesiredAccuracy = Windows.Devices.Geolocation.PositionAccuracy.Default,
                ReportInterval  = 0
            };

            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(8));
            var position  = await locator.GetGeopositionAsync().AsTask(cts.Token);

            p.Latitude         = position.Coordinate.Point.Position.Latitude;
            p.Longitude        = position.Coordinate.Point.Position.Longitude;
            p.LocationAccuracy = position.Coordinate.Accuracy;
        }
        catch (Exception)
        {
            // GPS no disponible o no habilitado — normal para tablets sin GPS
            // No loguear como error para no llenar el log
        }
    }

    // ────────────────────────────────────────────────
    // Helpers
    // ────────────────────────────────────────────────

    private static string RunCommand(string exe, string args)
    {
        var psi = new ProcessStartInfo(exe, args)
        {
            RedirectStandardOutput = true,
            UseShellExecute        = false,
            CreateNoWindow         = true,
        };
        using var proc = Process.Start(psi)!;
        var output = proc.StandardOutput.ReadToEnd();
        proc.WaitForExit(3000);
        return output;
    }

    [DllImport("user32.dll")]
    private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

    [StructLayout(LayoutKind.Sequential)]
    private struct LASTINPUTINFO
    {
        public uint cbSize;
        public uint dwTime;
    }

    private static bool IsScreenLocked()
    {
        // Detecta si el proceso "LogonUI" está corriendo = pantalla de bloqueo activa
        return Process.GetProcessesByName("LogonUI").Length > 0;
    }
}