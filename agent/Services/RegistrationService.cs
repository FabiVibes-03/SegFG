using System.Net.NetworkInformation;
using System.Runtime.Versioning;
using Microsoft.Win32;
using TabletMonitor.Models;

namespace TabletMonitor.Services;

/// <summary>
/// Gestiona el registro inicial del dispositivo y el almacenamiento seguro del token.
/// El token se guarda en HKLM\SOFTWARE\TabletMonitor — solo accesible por SYSTEM y admins.
/// </summary>
[SupportedOSPlatform("windows")]
public class RegistrationService
{
    private readonly ApiService _api;
    private readonly ILogger<RegistrationService> _logger;

    public RegistrationService(ApiService api, ILogger<RegistrationService> logger)
    {
        _api    = api;
        _logger = logger;
    }

    /// <summary>
    /// Si el dispositivo ya tiene token guardado, no hace nada.
    /// Si no tiene token, lo registra en el servidor y guarda el token.
    /// </summary>
    public async Task EnsureRegisteredAsync()
    {
        var existingToken = TokenStorage.GetToken();
        if (!string.IsNullOrEmpty(existingToken))
        {
            _logger.LogInformation("Dispositivo ya registrado (ID: {id})", TokenStorage.GetDeviceId());
            return;
        }

        _logger.LogInformation("Registrando dispositivo por primera vez...");

        var request = new RegisterRequest
        {
            Hostname   = Environment.MachineName,
            MacAddress = GetPrimaryMac(),
            OsVersion  = Environment.OSVersion.VersionString,
        };

        var response = await _api.RegisterAsync(request);

        if (response == null)
        {
            _logger.LogError("No se pudo registrar el dispositivo — servidor no disponible. Se reintentará al reiniciar.");
            return;
        }

        // Guardar token y device_id en registro de Windows
        TokenStorage.SaveToken(response.ApiToken, response.DeviceId);
        _logger.LogInformation("Dispositivo registrado. ID: {id}", response.DeviceId);
    }

    private static string GetPrimaryMac()
    {
        return NetworkInterface.GetAllNetworkInterfaces()
            .Where(n =>
                n.OperationalStatus == OperationalStatus.Up &&
                n.NetworkInterfaceType != NetworkInterfaceType.Loopback &&
                n.GetPhysicalAddress().ToString() != "")
            .OrderBy(n => n.NetworkInterfaceType == NetworkInterfaceType.Wireless80211 ? 0 : 1)
            .FirstOrDefault()
            ?.GetPhysicalAddress()
            .ToString()
            ?? Environment.MachineName; // fallback si no hay NIC
    }
}

/// <summary>
/// Almacena y recupera el token del registro de Windows (HKLM).
/// HKLM requiere privilegios de administrador para escribir — perfecto para un servicio del sistema.
/// </summary>
[SupportedOSPlatform("windows")]
public static class TokenStorage
{
    private const string RegistryPath = @"SOFTWARE\TabletMonitor";
    private const string TokenKey     = "ApiToken";
    private const string DeviceIdKey  = "DeviceId";

    public static void SaveToken(string token, string deviceId)
    {
        using var key = Registry.LocalMachine.CreateSubKey(RegistryPath);
        key.SetValue(TokenKey, token, RegistryValueKind.String);
        key.SetValue(DeviceIdKey, deviceId, RegistryValueKind.String);
    }

    public static string? GetToken()
    {
        using var key = Registry.LocalMachine.OpenSubKey(RegistryPath);
        return key?.GetValue(TokenKey) as string;
    }

    public static string? GetDeviceId()
    {
        using var key = Registry.LocalMachine.OpenSubKey(RegistryPath);
        return key?.GetValue(DeviceIdKey) as string;
    }

    public static void ClearToken()
    {
        using var key = Registry.LocalMachine.OpenSubKey(RegistryPath, writable: true);
        key?.DeleteValue(TokenKey, throwOnMissingValue: false);
        key?.DeleteValue(DeviceIdKey, throwOnMissingValue: false);
    }
}