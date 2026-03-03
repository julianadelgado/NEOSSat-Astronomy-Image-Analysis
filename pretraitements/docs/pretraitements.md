# Pré-traitements d'images

[Retour au README](/README.md)

## Éxécution du code

Installez les dépendances requises en premier.

`pip3 install -r "pretraitements/requirements.txt"`

Exécutez le serveur.

`uvicorn pretraitements.main:app --reload --host 0.0.0.0 --port 8000`

## Architecture

![Diagramme de classes UML](/pretraitements/docs/class.png)