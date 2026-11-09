probleme : cd C:\formation\datapilot; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install --upgrade pip; pip install -r requirements.txt

Le problème vient du fait que tu utilises CMD (Invite de commandes) et non PowerShell.

Dans CMD, le séparateur ; ne fonctionne pas comme dans PowerShell.

solution: py -3.14 -m venv .venv && .venv\Scripts\activate.bat && python -m pip install --upgrade pip && pip install -r requirements.txt




1- avantages:       - confidentialité, les données restent sur la machine en local
                    - pas besoin de l'internet pour utuliser un modéle
                    - pas de limite ou pas de cout liéé a chaque réquete
 Inconvénient: - il faut disposer de matriel
               - temps de reponse peuvent etre lente en comparison avec les services en lignes
               - il faut gérer l'instalation, les mise a jours et les maintenaces de modéles

 2-  Le premier appel doit télécharger le modèle depuis Internet, ce qui peut prendre du temps selon sa taille et la connexion.


 3 - Un environnement virtuel permet d'isoler les dépendances et les bibliothèques Python de chaque projet.

 4 - Cette information ne peut pas nécessairement se trouver directement dans la base de données, car le chiffre d'affaires est un indicateur calculé à partir de plusieurs informations : les commandes, leur statut, les paiements et les remboursements.   


 1. Présentation du problème

Lors de l'exécution de la commande :

ollama run qwen2.5:7b

L'erreur suivante est apparue :

pulling manifest
Error: max retries exceeded:
Get "https://....r2.cloudflarestorage.com/...":
dial tcp [2606:4700:113::1]:443: connectex:
Une tentative de connexion a échoué car l'hôte de connexion n'a pas répondu.

Symptômes constatés

Ollama démarrait correctement.

Le registre Ollama était accessible.

Le téléchargement du modèle échouait.

La connexion IPv6 vers Cloudflare R2 expirait.

Le problème persistait même avec un partage de connexion téléphonique.

2. Vérification de l'installation d'Ollama

Commande 1 : vérifier le chemin d'installation

where ollama

Résultat :

C:\Users\mayss\AppData\Local\Programs\Ollama\ollama.exe

Commande 2 : vérifier la version

ollama --version

Résultat :

ollama version is 0.40.15

Commande 3 : vérifier le serveur local

curl http://localhost:11434/api/version

Résultat :

{"version":"0.40.15"}

Conclusion : le serveur Ollama fonctionne localement.

3. Diagnostic de la connexion réseau

Test 1 : connexion au site officiel

curl -4 -I https://ollama.com

Résultat :

HTTP/1.1 200 OK

Conclusion : accès Internet en IPv4 fonctionnel.

Test 2 : connexion au registre Ollama

curl -4 -I https://registry.ollama.ai

Résultat :

HTTP/1.1 200 OK

Conclusion : le registre Ollama est accessible.

Test 3 : connexion au stockage Cloudflare R2 en IPv4

curl -4 -I https://dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

Résultat :

HTTP/1.1 400 Bad Request

Interprétation : le serveur Cloudflare répond. Le code 400 est attendu pour cette requête de test sans URL de téléchargement signée.

Test 4 : connexion au site officiel en IPv6

curl -6 -I https://ollama.com

Résultat :

curl: (6) Could not resolve host: ollama.com

Interprétation : la résolution DNS IPv6 n'a pas fonctionné pour ce test.

Test 5 : connexion au stockage Cloudflare R2 en IPv6

curl -6 -I https://dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

Résultat :

curl: (28) Failed to connect
Could not connect to server

Conclusion : la connexion IPv6 vers Cloudflare R2 échoue.

4. Vérification du DNS

Commande utilisée :

nslookup dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

Résultat :

DNS request timed out.

Serveur : UnKnown
Address: 10.138.73.11

Nom :
dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

Addresses:
2606:4700:113::1
2606:4700:2ff9::1
172.64.66.1
172.64.190.1

Interprétation :

Le DNS a répondu après un délai d'attente.

Des adresses IPv6 et IPv4 ont été obtenues.

La connexion IPv4 fonctionne.

La connexion IPv6 vers Cloudflare échoue.

5. Vérification des modèles installés

Commande :

ollama list

Résultat :

NAME    ID    SIZE    MODIFIED

Conclusion : aucun modèle n'était encore téléchargé localement.

6. Correction appliquée : privilégier IPv4

L'objectif est de demander à Windows de privilégier les adresses IPv4 lors de la sélection des adresses réseau.

Étape 1 : ouvrir CMD en administrateur

Cliquer sur Démarrer.

Rechercher CMD.

Faire un clic droit.

Sélectionner « Exécuter en tant qu'administrateur ».

Étape 2 : modifier la priorité IPv4

Exécuter :

netsh interface ipv6 set prefixpolicy ::ffff:0:0/96 50 4

Cette commande augmente la priorité du préfixe IPv4 mappé dans la politique de sélection des adresses Windows.

Attention : cette modification ne force pas directement tous les programmes à utiliser IPv4. Il faut vérifier que l'application respecte la politique de sélection Windows.

Étape 3 : relancer le téléchargement

ollama pull qwen2.5:7b

Attendre la fin du téléchargement.

Étape 4 : lancer le modèle

ollama run qwen2.5:7b

7. Vérification finale

Une fois le téléchargement terminé :

ollama list

Le modèle qwen2.5:7b doit apparaître dans la liste.

Vérifier également :

ollama ps

Cette commande affiche les modèles actuellement chargés en mémoire.

Enfin, tester le modèle :

ollama run qwen2.5:7b

Exemple de question :

Bonjour, présente-toi et explique-moi ce que tu peux faire.

8. Restaurer la configuration réseau initiale

Si nécessaire, restaurer la priorité IPv4 par défaut :

netsh interface ipv6 set prefixpolicy ::ffff:0:0/96 35 4

Cette commande restaure la priorité habituelle du préfixe IPv4 mappé.

Il n'est pas nécessaire de désactiver complètement IPv6.

9. Liste récapitulative des commandes

where ollama

ollama --version

curl http://localhost:11434/api/version

curl -4 -I https://ollama.com

curl -4 -I https://registry.ollama.ai

curl -4 -I https://dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

curl -6 -I https://ollama.com

curl -6 -I https://dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

nslookup dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com

ollama list

netsh interface ipv6 set prefixpolicy ::ffff:0:0/96 50 4

ollama pull qwen2.5:7b

ollama run qwen2.5:7b

ollama ps

10. Conclusion

Le problème rencontré ne provenait pas du fonctionnement du serveur Ollama lui-même.

Les tests ont permis de constater :

Un serveur Ollama local opérationnel.

Un registre Ollama accessible en IPv4.

Un serveur Cloudflare R2 accessible en IPv4.

Une connexion IPv6 vers Cloudflare R2 qui échouait.

Une résolution DNS qui présentait également un délai d'attente.

La correction envisagée consiste à privilégier IPv4 dans la politique de sélection des adresses Windows, puis à relancer le téléchargement du modèle.

Important : le diagnostic IPv6 est établi par les tests réalisés. La correction par priorité IPv4 doit être considérée comme validée uniquement après confirmation du téléchargement réussi de qwen2.5:7b.



