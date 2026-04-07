using TabletMonitor.Services;

namespace TabletMonitor;

public class Worker : BackgroundService
{
    private readonly ILogger<Worker> _logger;
    private readonly TelemetryService _telemetry;
    private readonly ApiService _api;
    private readonly CommandExecutor _executor;
    private readonly IConfiguration _config;

    public Worker(
        ILogger<Worker> logger,
        TelemetryService telemetry,
        ApiService api,
        CommandExecutor executor,
        IConfiguration config)
    {
        _logger   = logger;
        _telemetry = telemetry;
        _api       = api;
        _executor  = executor;
        _config    = config;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var intervalSeconds = _config.GetValue<int>("Agent:HeartbeatIntervalSeconds", 30);
        var interval        = TimeSpan.FromSeconds(intervalSeconds);

        _logger.LogInformation("TabletMonitor iniciado. Intervalo: {s}s", intervalSeconds);

        // Esperar un momento antes del primer heartbeat
        await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await SendHeartbeatAsync();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error en ciclo de heartbeat");
            }

            await Task.Delay(interval, stoppingToken);
        }
    }

    private async Task SendHeartbeatAsync()
    {
        // 1. Recopilar telemetría
        var payload = await _telemetry.CollectAsync();

        // 2. Enviar al servidor
        var response = await _api.SendHeartbeatAsync(payload);

        if (response == null)
        {
            _logger.LogWarning("No se pudo contactar el servidor");
            return;
        }

        _logger.LogInformation(
            "Heartbeat OK — Batería: {bat}% | CPU: {cpu}% | RAM: {ram}MB | SSID: {ssid}",
            payload.BatteryLevel,
            payload.CpuUsage?.ToString("F1") ?? "N/A",
            payload.RamUsedMb,
            payload.Ssid ?? "N/A"
        );

        // 3. Ejecutar comandos pendientes recibidos del servidor
        if (response.Commands.Count > 0)
        {
            _logger.LogInformation("Recibidos {n} comando(s) del servidor", response.Commands.Count);
            foreach (var cmd in response.Commands)
            {
                await _executor.ExecuteAsync(cmd);
            }
        }
    }
}