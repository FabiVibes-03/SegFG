using System.Text.Json.Serialization;

namespace TabletMonitor.Models;

/// <summary>
/// Datos que el agente envía al servidor en cada heartbeat.
/// Los campos son opcionales para soportar tablets sin GPS o sin batería.
/// </summary>
public class HeartbeatPayload
{
    // ── Red ─────────────────────────────────────────
    [JsonPropertyName("ip_address")]
    public string? IpAddress { get; set; }

    [JsonPropertyName("ssid")]
    public string? Ssid { get; set; }

    [JsonPropertyName("mac_address")]
    public string? MacAddress { get; set; }

    // ── Batería ──────────────────────────────────────
    [JsonPropertyName("battery_level")]
    public int? BatteryLevel { get; set; }

    [JsonPropertyName("battery_charging")]
    public bool? BatteryCharging { get; set; }

    [JsonPropertyName("battery_status")]
    public string? BatteryStatus { get; set; }

    // ── Hardware ─────────────────────────────────────
    [JsonPropertyName("cpu_usage")]
    public double? CpuUsage { get; set; }

    [JsonPropertyName("ram_used_mb")]
    public int? RamUsedMb { get; set; }

    [JsonPropertyName("ram_total_mb")]
    public int? RamTotalMb { get; set; }

    [JsonPropertyName("disk_free_gb")]
    public double? DiskFreeGb { get; set; }

    [JsonPropertyName("disk_total_gb")]
    public double? DiskTotalGb { get; set; }

    // ── GPS (opcional) ───────────────────────────────
    [JsonPropertyName("latitude")]
    public double? Latitude { get; set; }

    [JsonPropertyName("longitude")]
    public double? Longitude { get; set; }

    [JsonPropertyName("location_accuracy")]
    public double? LocationAccuracy { get; set; }

    // ── Sistema ──────────────────────────────────────
    [JsonPropertyName("os_version")]
    public string? OsVersion { get; set; }

    [JsonPropertyName("uptime_seconds")]
    public int? UptimeSeconds { get; set; }

    [JsonPropertyName("screen_locked")]
    public bool? ScreenLocked { get; set; }

    [JsonPropertyName("active_user")]
    public string? ActiveUser { get; set; }
}

/// <summary>
/// Respuesta del servidor al heartbeat — puede incluir comandos a ejecutar.
/// </summary>
public class HeartbeatResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "ok";

    [JsonPropertyName("commands")]
    public List<RemoteCommand> Commands { get; set; } = new();
}

/// <summary>
/// Comando remoto recibido del servidor.
/// </summary>
public class RemoteCommand
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("command")]
    public string Command { get; set; } = "";

    /// <summary>
    /// Datos extra según el tipo de comando.
    /// Ej: { "message": "Devuelve esta tablet al encargado" }
    /// </summary>
    [JsonPropertyName("payload")]
    public Dictionary<string, object>? Payload { get; set; }
}

/// <summary>
/// Datos de registro del dispositivo enviados al servidor por primera vez.
/// </summary>
public class RegisterRequest
{
    [JsonPropertyName("hostname")]
    public string Hostname { get; set; } = "";

    [JsonPropertyName("mac_address")]
    public string MacAddress { get; set; } = "";

    [JsonPropertyName("os_version")]
    public string? OsVersion { get; set; }
}

/// <summary>
/// Respuesta del servidor al registrar el dispositivo.
/// </summary>
public class RegisterResponse
{
    [JsonPropertyName("device_id")]
    public string DeviceId { get; set; } = "";

    [JsonPropertyName("api_token")]
    public string ApiToken { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}