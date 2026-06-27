import time
import sys
from web3 import Web3
from eth_abi import encode, decode

RPC_URL = "https://rpc.ritualfoundation.org"
AGENT_ADDRESS = "0x468d76dbF5B82fE1B1913C2C81a951F6A553ea10"
WALLET_ADDRESS = "0xe91f900f9a3a8e390bf7f62c100447c3f2d212d0"
WALLET_REGISTRY = "0x532F0dF0896F353d8C3DD8cc134e8129DA2a3948"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
checksum_agent = w3.to_checksum_address(AGENT_ADDRESS)
checksum_registry = w3.to_checksum_address(WALLET_REGISTRY)

def get_agent_balance():
    try:
        # Query balance in Ritual Wallet registry
        raw_bal = w3.eth.call({
            "to": checksum_registry,
            "data": w3.keccak(text="balanceOf(address)")[:4] + encode(['address'], [checksum_agent])
        })
        bal_wei = int.from_bytes(raw_bal, byteorder='big')
        return bal_wei / 10**18
    except Exception:
        return 0.0

def get_wake_mode():
    try:
        raw_mode = w3.eth.call({
            "to": checksum_agent,
            "data": w3.keccak(text="wakeMode()")[:4]
        })
        return int.from_bytes(raw_mode, byteorder='big')
    except Exception:
        return -1

def decode_callback_data(tx_input):
    try:
        # onSovereignAgentResult(bytes32,bytes) -> selector is 0x8ca12055
        if not tx_input.startswith(b'\x8c\xa1\x20\x55'):
            return None
        
        # input layout: selector (4b) + taskId (32b) + offset (32b) + length (32b) + data...
        # We can extract the bytes starting from offset 100 (which is 4 + 32 + 32 + 32)
        # Or decode properly using eth-abi
        _, decoded_bytes = decode(['bytes32', 'bytes'], tx_input[4:])
        return decoded_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"[Error decoding: {e}]"

def main():
    print("==================================================")
    print("        RITUAL SOVEREIGN AGENT MONITOR            ")
    print("==================================================")
    print(f"Agent Address:  {AGENT_ADDRESS}")
    print(f"Owner Address:  {WALLET_ADDRESS}")
    print("--------------------------------------------------")
    
    # Check initial state
    mode = get_wake_mode()
    mode_str = "ARMED" if mode == 1 else "STOPPED" if mode == 0 else "UNKNOWN"
    balance = get_agent_balance()
    
    print(f"Current Status:  {mode_str}")
    print(f"Current Balance: {balance:.18f} RITUAL")
    print("==================================================")
    print("Listening for execution callback transactions...")
    print("Press Ctrl+C to stop.\n")
    
    last_checked_block = w3.eth.block_number
    
    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_checked_block:
                for b_num in range(last_checked_block + 1, current_block + 1):
                    block = w3.eth.get_block(b_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx['to'] and tx['to'].lower() == AGENT_ADDRESS.lower():
                            print(f"\n[Detected Run Callback] Block {b_num} | Tx: {tx['hash'].hex()}")
                            # Decode input
                            ai_output = decode_callback_data(tx['input'])
                            if ai_output:
                                print("-" * 50)
                                print("AI RESPONSE:")
                                print(ai_output)
                                print("-" * 50)
                            else:
                                print(f"Non-callback transaction sent to agent. Input: {tx['input'].hex()[:64]}...")
                            
                            # Print updated balance
                            print(f"New Balance: {get_agent_balance():.18f} RITUAL")
                last_checked_block = current_block
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break
        except Exception as e:
            print(f"Error checking network: {e}")
        time.sleep(6)

if __name__ == "__main__":
    main()
