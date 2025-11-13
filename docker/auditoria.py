import time
import os

log_path = "/var/logs/api/instrucoes.log"

def processar_liquidacao():
    if not os.path.exists(log_path):
        return
    with open(log_path, "r") as f:
        linhas = f.readlines()
    novas_linhas = []
    for linha in linhas:
        if "AGUARDANDO_LIQUIDACAO" in linha:
            novas_linhas.append(linha.replace("AGUARDANDO_LIQUIDACAO", "LIQUIDADO"))
        else:
            novas_linhas.append(linha)
    with open(log_path, "w") as f:
        f.writelines(novas_linhas)

if __name__ == "__main__":
    processar_liquidacao()
