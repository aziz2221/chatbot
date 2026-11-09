"""explorer/premier_appel.py — Premier appel HTTP à Ollama."""
import sys
import time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # pour importer config
import config
payload = {
"model": config.LLM_MODEL,
"messages": [
# TODO : un message "user" qui demande, en une phrase, ce qu'est un panier moyen
{"role": "user", "content": "Qu'est-ce qu'un panier moyen ?"}
],
"stream": False,
"options": {"temperature": config.LLM_TEMPERATURE},
}
debut = time.perf_counter()
reponse = requests.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=120)
duree = time.perf_counter() - debut
# TODO : afficher le code HTTP, le texte de la réponse, les deux compteurs de tokens et 
print("Code HTTP :", reponse.status_code)
donnees = reponse.json()
print("Réponse :", donnees["message"]["content"])
print("Tokens lus :", donnees.get("prompt_eval_count"))
print("Tokens générés :", donnees.get("eval_count"))
print("Durée :", round(duree, 2), "secondes")