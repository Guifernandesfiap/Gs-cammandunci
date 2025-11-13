from flask import Flask, request
import os

app = Flask(__name__)
saldo = int(os.getenv("RESERVA_BANCARIA_SALDO", "0"))
log_path = "/var/logs/api/instrucoes.log"

@app.route("/pix", methods=["POST"])
def pix():
    valor = int(request.json.get("valor", 0))
    if valor <= saldo:
        with open(log_path, "a") as f:
            f.write(f"PIX {valor} AGUARDANDO_LIQUIDACAO\n")
        return {"status": "AGUARDANDO_LIQUIDACAO"}, 200
    else:
        return {"status": "SALDO_INSUFICIENTE"}, 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
