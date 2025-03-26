import asyncio
import websockets
import json
from api_key_secrets import api_key_demo, id_usuario


api_key = api_key_demo
url = f'wss://ws.binaryws.com/websockets/v3?app_id={id_usuario}'

STOP_LOSS = -10  # Limite de perda 
TAKE_PROFIT = 3  # Meta de lucro 
saldo_atual = 0  # Armazena o lucro ou perda
ultimo_digitos = []  # Lista para armazenar os últimos dois dígitos dos preços

async def connect():
    global saldo_atual  # Para atualizar o saldo durante a execução
        
    async with websockets.connect(url) as websocket:
        # Autentica o bot com a chave da API
        auth_request = {
            "authorize": api_key
        }
        await websocket.send(json.dumps(auth_request))
        await websocket.recv()  # Aguarda resposta de autenticação

        # Solicita informações sobre o saldo da conta
        account_request = {
            "balance": 1  # Requisição para saldo
        }
        await websocket.send(json.dumps(account_request))
        balance_response = await websocket.recv()
        saldo = json.loads(balance_response)
        print(f'Saldo da conta: {saldo["balance"]["balance"]}')  # Exibe saldo atual da Conta

        # Receber ticks do mercado R_100
        tick_request = {"ticks": "R_100"}  # Mercado R_100 - Tem varios outros mercados também
        await websocket.send(json.dumps(tick_request))

        while True:
            # Verifica se o saldo atingiu o limite de perda ou lucro
            if saldo_atual <= STOP_LOSS:
                print("🔴 Stop Loss atingido! Encerrando o bot.")
                break
            if saldo_atual >= TAKE_PROFIT:
                print("🟢 Take Profit atingido! Encerrando o bot.")
                break

            # Recebe resposta com informações do tick
            response = await websocket.recv()
            data = json.loads(response)

            # Verifica se a resposta contém dados de tick
            if "tick" in data:
                ultimo_preco = float(data["tick"]["quote"])  # Preço atual
                preco_formatado = f"{ultimo_preco:.2f}"
                ultimo_digito = preco_formatado[-1]  # Último dígito do preço
                print(f"\rPreço: {preco_formatado} | Último Dígito: {ultimo_digito}", end=' ', flush=True)  # Exibe o preço e o último dígito

                # Armazena os últimos dois dígitos
                ultimo_digitos.append(ultimo_digito)
                if len(ultimo_digitos) > 2:
                    ultimo_digitos.pop(0)

                # Verifica se os dois últimos dígitos são 0
                if ultimo_digitos == ["0", "0"]:
                    print()
                    print('--' * 20, flush=False)
                    print("\n⚡ Dois zero detectado! Fazendo a aposta...")

                    # Envia ordem de compra, apostando que o próximo dígito não será 0
                    trade_request = {
                        "buy": 1,
                        "price": 0.35,  # Valor de aposta
                        "parameters": {
                            "amount": 0.35,  # Quantia apostada
                            "basis": "stake",
                            "contract_type": "DIGITDIFF",  # O Tipo de contrato
                            "currency": "USD",
                            "duration": 1,  # 1 tick de duração
                            "duration_unit": "t",
                            "symbol": "R_100",
                            "barrier": "0"
                        }
                    }
                    await websocket.send(json.dumps(trade_request))
                    trade_response = await websocket.recv()
                    trade_data = json.loads(trade_response)
                    if "buy" in trade_data:
                        compra = trade_data["buy"]
                        contrato_id = compra.get("contract_id", "N/A")  # ID do contrato
                        preco = compra.get("buy_price", "N/A")  # Preço de compra

                        print(f"Ordem enviada!\nContrato ID: {contrato_id}\nPreço: {preco}")

                    # Atualiza saldo com o resultado da operação
                    if "buy" in trade_data:
                        contrato_id = trade_data["buy"]["contract_id"]
                        
                        # Aguardar o resultado do contrato
                        while True:
                            result_request = {"proposal_open_contract": 1, "contract_id": contrato_id}
                            await websocket.send(json.dumps(result_request))
                            result_response = await websocket.recv()
                            result_data = json.loads(result_response)

                            if "proposal_open_contract" in result_data:
                                contract = result_data["proposal_open_contract"]

                                if contract.get("is_sold", False):  # Se o contrato foi fechado
                                    lucro = contract["profit"]
                                    saldo_atual += lucro  # Atualiza o saldo com o lucro
                                    if lucro > 0:
                                        print(f"✅ Resultado da operação: {lucro:.2f} USD | Saldo Atual: {saldo_atual:.2f} USD")
                                        print()
                                        print('--' * 20)
                                    else:
                                        print(f"❌ Resultado da operação: {lucro:.2f} USD | Saldo Atual: {saldo_atual:.2f} USD")
                                        print()
                                        print('--' * 20)
                                    break
        

# Iniciar a conexão
asyncio.get_event_loop().run_until_complete(connect())
