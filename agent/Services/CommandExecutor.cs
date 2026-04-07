using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using TabletMonitor.Models;

namespace TabletMonitor.Services;

/// <summary>
/// Ejecuta los comandos remotos enviados desde el dashboard.
/// Comandos disponibles: lock, shutdown, alarm, message
/// </summary>
[SupportedOSPlatform("windows")]
public class CommandExecutor
{
    private readonly ILogger<CommandExecutor> _logger;

    public CommandExecutor(ILogger<CommandExecutor> logger)
    {
        _logger = logger;
    }

    public async Task ExecuteAsync(RemoteCommand cmd)
    {
        _logger.LogInformation("Ejecutando comando: {cmd}", cmd.Command);

        try
        {
            switch (cmd.Command.ToLower())
            {
                case "lock":
                    ExecuteLock();
                    break;

                case "shutdown":
                    ExecuteShutdown();
                    break;

                case "alarm":
                    await ExecuteAlarmAsync();
                    break;

                case "message":
                    var message = cmd.Payload?.GetValueOrDefault("message")?.ToString()
                        ?? "Mensaje del administrador";
                    ExecuteMessage(message);
                    break;

                default:
                    _logger.LogWarning("Comando desconocido recibido: {cmd}", cmd.Command);
                    break;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error ejecutando comando {cmd}", cmd.Command);
        }
    }

    // ────────────────────────────────────────────────
    // Lock — bloquea la pantalla inmediatamente
    // ────────────────────────────────────────────────

    [DllImport("user32.dll")]
    private static extern bool LockWorkStation();

    private void ExecuteLock()
    {
        _logger.LogInformation("Bloqueando pantalla...");
        LockWorkStation();
    }

    // ────────────────────────────────────────────────
    // Shutdown — apaga la tablet en 30 segundos
    // (30s para que el agente pueda confirmar al servidor si se implementa)
    // ────────────────────────────────────────────────

    private void ExecuteShutdown()
    {
        _logger.LogInformation("Apagando dispositivo en 30 segundos...");

        // Mostrar mensaje antes de apagar
        ExecuteMessage("⚠️ Este dispositivo se apagará en 30 segundos por orden del administrador.");

        // /s = shutdown, /t 30 = en 30 segundos, /f = forzar cierre de apps
        RunCommand("shutdown", "/s /t 30 /f /c \"Apagado remoto por TabletMonitor\"");
    }

    // ────────────────────────────────────────────────
    // Alarm — reproduce sonido de alerta
    // ────────────────────────────────────────────────

    private async Task ExecuteAlarmAsync()
    {
        _logger.LogInformation("Activando alarma sonora...");

        // Subir volumen al máximo primero
        RunCommand("nircmd", "setsysvolume 65535"); // NirCmd si está disponible

        // Reproducir beeps de alerta repetidamente por 30 segundos
        var endTime = DateTime.Now.AddSeconds(30);
        while (DateTime.Now < endTime)
        {
            Console.Beep(1000, 500); // 1000 Hz, 500ms
            await Task.Delay(600);
            Console.Beep(800, 500);
            await Task.Delay(600);
        }
    }

    // ────────────────────────────────────────────────
    // Message — muestra un mensaje en pantalla via msg.exe
    // ────────────────────────────────────────────────

    private void ExecuteMessage(string message)
    {
        _logger.LogInformation("Mostrando mensaje en pantalla: {msg}", message);

        // msg.exe envía un mensaje popup a la sesión activa del usuario
        // * = todos los usuarios conectados
        RunCommand("msg", $"* /time:60 \"{message}\"");
    }

    // ────────────────────────────────────────────────
    // Helper
    // ────────────────────────────────────────────────

    private static void RunCommand(string exe, string args)
    {
        try
        {
            var psi = new ProcessStartInfo(exe, args)
            {
                UseShellExecute        = false,
                CreateNoWindow         = true,
                RedirectStandardOutput = true,
                RedirectStandardError  = true,
            };
            using var proc = Process.Start(psi);
            proc?.WaitForExit(5000);
        }
        catch (Exception)
        {
            // Algunos comandos pueden no estar disponibles — no es crítico
        }
    }
}