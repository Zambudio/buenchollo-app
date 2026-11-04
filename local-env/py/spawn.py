"""Lanza un proceso en segundo plano, desacoplado de la consola, e imprime su PID.

`Start-Process -RedirectStandardOutput` de PowerShell hace que el hijo
herede TODOS los handles heredables del padre: si bct-local.ps1 se ejecuta
con la salida canalizada (agentes, CI), la tubería no se cierra nunca y el
comando se queda colgado. subprocess.Popen en Windows solo pasa al hijo los
handles de stdout/stderr indicados.

Uso: python spawn.py <log_sin_extension> <cwd> <exe> [args...]
"""

import subprocess
import sys

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
# Sacar el proceso del job object de quien lanza bct-local (terminal, IDE,
# agente de IA): al cerrarse ese job, Windows mata a todos sus descendientes
# y los servicios morían sin dejar rastro en el log.
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
BASE_FLAGS = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW


def main() -> None:
    log_base, cwd, *cmd = sys.argv[1:]
    with open(f"{log_base}.log", "wb") as out, open(f"{log_base}.err.log", "wb") as err:
        kwargs = dict(cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, close_fds=True)
        try:
            proc = subprocess.Popen(cmd, creationflags=BASE_FLAGS | CREATE_BREAKAWAY_FROM_JOB, **kwargs)
        except PermissionError:
            # El job no permite salir de él: se lanza dentro (comportamiento anterior).
            proc = subprocess.Popen(cmd, creationflags=BASE_FLAGS, **kwargs)
    print(proc.pid)


if __name__ == "__main__":
    main()
