using System.Diagnostics;
using System.Runtime.Versioning;

namespace TabletMonitor.Services;

/// <summary>
/// Instala y desinstala el agente como Windows Service.
/// Uso:
///   TabletMonitor.exe install    (requiere ejecutar como administrador)
///   TabletMonitor.exe uninstall
/// </summary>
[SupportedOSPlatform("windows")]
public static class ServiceInstaller
{
    private const string ServiceName        = "TabletMonitor";
    private const string ServiceDisplayName = "Tablet Monitor Agent";
    private const string ServiceDescription = "Monitoreo de dispositivo - TabletMonitor";

    public static void Install()
    {
        var exePath = Environment.ProcessPath
            ?? System.Reflection.Assembly.GetExecutingAssembly().Location;

        Console.WriteLine($"Instalando servicio '{ServiceName}'...");
        Console.WriteLine($"Ejecutable: {exePath}");

        // Crear el servicio
        RunSc($"create {ServiceName} " +
              $"binPath= \"{exePath}\" " +
              $"DisplayName= \"{ServiceDisplayName}\" " +
              $"start= auto " +       // inicia automáticamente con Windows
              $"obj= LocalSystem");   // corre como SYSTEM — máximos privilegios

        // Agregar descripción
        RunSc($"description {ServiceName} \"{ServiceDescription}\"");

        // Configurar recuperación automática si falla:
        // 1er fallo: reiniciar en 10s
        // 2do fallo: reiniciar en 30s
        // Fallos siguientes: reiniciar en 60s
        RunSc($"failure {ServiceName} reset= 86400 " +
              $"actions= restart/10000/restart/30000/restart/60000");

        // Proteger el servicio para que no pueda detenerse sin ser admin
        // (requiere sc sdset — permisos avanzados)
        ProtectService();

        // Iniciar el servicio ahora
        RunSc($"start {ServiceName}");

        Console.WriteLine($"✅ Servicio '{ServiceName}' instalado e iniciado.");
        Console.WriteLine("Para verificar: services.msc o 'sc query TabletMonitor'");
    }

    public static void Uninstall()
    {
        Console.WriteLine($"Desinstalando servicio '{ServiceName}'...");

        RunSc($"stop {ServiceName}");
        System.Threading.Thread.Sleep(2000);
        RunSc($"delete {ServiceName}");

        // Limpiar token del registro de Windows
        TokenStorage.ClearToken();

        Console.WriteLine($"✅ Servicio '{ServiceName}' desinstalado.");
    }

    private static void ProtectService()
    {
        // DACL que permite a SYSTEM y Admins controlarlo, pero NO a usuarios normales
        // D: = DACL, (A;;RPWPRCRCRPWP;;;SY) = SYSTEM, (A;;RPWPRCRC;;;BA) = Built-in Admins
        // Los usuarios normales (BU) solo pueden leer, no detener/modificar
        var sdString = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)";
        RunSc($"sdset {ServiceName} \"{sdString}\"");
    }

    private static void RunSc(string args)
    {
        try
        {
            var psi = new ProcessStartInfo("sc.exe", args)
            {
                UseShellExecute        = false,
                CreateNoWindow         = true,
                RedirectStandardOutput = true,
                RedirectStandardError  = true,
            };
            using var proc = Process.Start(psi)!;
            var output = proc.StandardOutput.ReadToEnd();
            proc.WaitForExit(10000);

            if (!string.IsNullOrWhiteSpace(output))
                Console.WriteLine(output.Trim());
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[sc.exe error] {ex.Message}");
        }
    }
}