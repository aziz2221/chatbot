# DataPilot — ShopNova

Assistant data analyst local construit en Python : il répond aux questions sur les ventes 2024–2025 avec SQLite en lecture seule et consulte les documents métier avec une recherche sémantique (RAG). L'agent utilise Ollama en local et Gradio pour l'interface web.

## Installation

Depuis la racine du projet, sous Windows PowerShell :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:7b
```

Python 3.11 à 3.13 est recommandé. Si votre ordinateur a 8 Go de RAM, vous pouvez choisir `qwen2.5:3b` avec `$env:LLM_MODEL = "qwen2.5:3b"`. Au premier démarrage, le modèle d'embedding `paraphrase-multilingual-MiniLM-L12-v2` est également téléchargé par Sentence Transformers.

## Démarrer

Ollama doit être lancé, puis depuis la racine du projet avec l'environnement virtuel activé :

```powershell
python ui.py
```

Ouvrez l'adresse locale indiquée par Gradio (par défaut `http://127.0.0.1:7860`). Pour utiliser l'agent dans le terminal, lancez `python agent.py`. `python explorer/premier_appel.py` permet de vérifier séparément l'API Ollama.

Les réglages se trouvent dans `config.py` et peuvent être remplacés par des variables d'environnement. La base se trouve dans `data/ecommerce.db`; `data/create_db.py` permet de la régénérer selon les options du script.

## Vérification et évaluation

```powershell
pytest -q
python evaluation.py
python explorer/hit_rate.py
```

Les tests unitaires utilisent des doublures et n'ont pas besoin d'Ollama. Les deux scripts d'évaluation utilisent un vrai modèle et peuvent nécessiter le téléchargement des embeddings et le démarrage d'Ollama. Le banc d'évaluation écrit ses résultats dans `logs/banc_resultats.csv`; les appels LLM sont ajoutés à `logs/llm_exchanges.jsonl`.

## Sécurité et limites

L'outil SQL n'accepte que des requêtes de lecture, ouvre SQLite en mode `ro`, limite le nombre de lignes et prend en charge les paramètres SQL. Les réponses du modèle restent à vérifier, notamment avant une décision métier. Les journaux peuvent contenir les questions posées : protégez et purgez `logs/` selon les besoins de confidentialité.
