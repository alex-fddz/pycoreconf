# XPath Database API - Documentation

## Vue d'ensemble

Le **XPath Database API** fournit une interface haut niveau pour accéder et modifier des données CORECONF/CBOR en utilisant une syntaxe de chemin XPath-like. Cette API cache complètement la complexité des SIDs (Semantic Identifiers) et des structures CBOR.

### Avantages

- ✅ Interface intuitive basée sur des chemins XPath
- ✅ Conversion automatique CBOR ↔ JSON
- ✅ Support des identités YANG (identityref) avec noms lisibles
- ✅ Opérateurs Python natifs (=, +=, -=, del, etc.)
- ✅ Gestion automatique des clés de listes
- ✅ Création d'entrées automatiques

---

## Installation et Setup

### Initialiser un modèle CORECONF

```python
import pycoreconf

# Créer un modèle à partir d'un fichier SID
model = pycoreconf.CORECONFModel("/path/to/your/model.sid")

# Charger les données CBOR dans une base de données
with open("data.cbor", "rb") as f:
    cbor_data = f.read()

db = model.loadDB(cbor_data)
```

---

## Syntaxe XPath

### Format général

```
/root/container[key1='value1'][key2='value2']/leaf
 │    │         └─── Prédicats (clés de liste) ───────┘
 │    │
 │    └─── Segments navigant l'arborescence YANG
 │
 └─── Racine absolue
```

### Éléments

- **Segments** : Noms d'éléments YANG (containers, lists, leaves)
- **Prédicats** : `[key='value']` pour identifier des entrées spécifiques dans une liste
- **Identités** : Les valeurs `identityref` utilisent les noms d'identité (pas les SIDs)

### Exemples

```python
# Accéder à un container
db["/root/container"]

# Accéder à une feuille dans un container simple
db["/root/container/leaf"]

# Accéder à une entrée de liste (1 clé)
db["/items/item[id='1']/value"]

# Accéder à une entrée de liste (2 clés)
db["/measurements/measurement[type='temp'][id='0']/value"]

# Accéder à une entrée de liste (avec identité)
db["/sensors/sensor[category='temperature'][location='room-1']/reading"]
```

---

## API - Lecture

### Lire une valeur

```python
# Lire une feuille (leaf)
value = db["/measurements/measurement[type='solar'][id='0']/value"]
print(value)  # >>> 1050

# Lire un container entier
entry = db["/measurements/measurement[type='solar'][id='0']"]
print(entry)
# >>> {
#       'type': 'solar-radiation',  # identityref converti en nom d'identité
#       'id': 0,                     # clé numérique
#       'value': 1050,
#       'precision': 2,
#       ...
#     }

# Lire une branche entière
all_measurements = db["/measurements"]
```

### Caractéristiques

- Les valeurs `identityref` sont **automatiquement converties** en noms d'identité lisibles
- Les types de données sont préservés (int, str, etc.)
- Une copie profonde (deep copy) est retournée pour éviter les modifications accidentelles

---

## API - Écriture

### Écrire une valeur simple

```python
# Écrire une feuille dans une liste
db["/measurements/measurement[type='solar'][id='0']/value"] = 2000

# Vérifier
assert db["/measurements/measurement[type='solar'][id='0']/value"] == 2000
```

### Opérateurs in-place

```python
# Incrémenter
db["/measurements/measurement[type='solar'][id='0']/counter"] += 10

# Décrémenter
db["/measurements/measurement[type='solar'][id='0']/counter"] -= 5

# Multiplication et autres opérateurs aussi supportés!
db["/measurements/measurement[type='solar'][id='0']/value"] *= 1.5
```

### Écrire un container entier

```python
new_entry = {
    'type': 'wind-speed',
    'id': 2,
    'value': 450,
    'precision': 1
}

db["/measurements/measurement[type='wind-speed'][id='2']"] = new_entry
```

### Créer des entrées automatiquement

Pour l'écriture, si une entrée de liste n'existe pas, elle est **créée automatiquement**:

```python
# Cette entrée n'existe pas - elle sera créée!
db["/measurements/measurement[type='humidity'][id='5']/precision"] = 2

# L'entrée est maintenant:
# {
#   'type': 'humidity',      # clés initiales
#   'id': 5,
#   'precision': 2           # la valeur qu'on a écrite
# }

# On peut écrire d'autres champs après:
db["/measurements/measurement[type='humidity'][id='5']/value"] = 650
```

---

## API - Suppression

### Supprimer une feuille (champ spécifique)

```python
# Supprimer uniquement le champ 'precision'
del db["/measurements/measurement[type='solar'][id='0']/precision"]

# L'entrée existe toujours, mais sans le champ 'precision'
entry = db["/measurements/measurement[type='solar'][id='0']"]
# 'precision' n'est pas dans entry
```

### Supprimer une entrée complète

```python
# Supprimer l'entrée entière
del db["/measurements/measurement[type='solar'][id='0']"]

# Essayer de lire l'entrée lève une KeyError
try:
    db["/measurements/measurement[type='solar'][id='0']/value"]
except KeyError:
    print("L'entrée a été supprimée")
```

---

## Conversion de données

### Exporter en JSON

```python
# Obtenir une représentation JSON
json_str = db.to_json()

# Utiliser avec json.loads()
import json
data_dict = json.loads(json_str)
```

### Exporter en CBOR

```python
# Obtenir les données CBOR binaires
cbor_bytes = db.to_cbor()

# Sauvegarder
with open("modified.cbor", "wb") as f:
    f.write(cbor_bytes)
```

---

## Flux de travail complet

### Exemple: Lire → Modifier → Sauvegarder

```python
import pycoreconf
import json

# 1. Créer le modèle
model = pycoreconf.CORECONFModel("/path/to/model.sid")

# 2. Charger les données
with open("data.cbor", "rb") as f:
    db = model.loadDB(f.read())

# 3. Lire une valeur
old_value = db["/measurements/measurement[type='temp'][id='0']/value"]
print(f"Ancienne valeur: {old_value}")

# 4. Modifier
db["/measurements/measurement[type='temp'][id='0']/value"] = old_value + 100

# 5. Vérifier
new_value = db["/measurements/measurement[type='temp'][id='0']/value"]
print(f"Nouvelle valeur: {new_value}")

# 6. Exporter JSON (pour inspection)
json_data = json.loads(db.to_json())
print(json.dumps(json_data, indent=2))

# 7. Sauvegarder en CBOR
cbor_bytes = db.to_cbor()
with open("data_modified.cbor", "wb") as f:
    f.write(cbor_bytes)
```

---

## Points clés - À retenir

### ✅ Automatique

| Aspect | Comportement |
|--------|--------------|
| **Créer entrées** | Écrire sur une clé inexistante crée l'entrée |
| **Convertir identités** | SID ↔ Nom d'identité automatiquement |
| **Gérer les types** | int, str, etc. préservés et convertis correctement |
| **CBOR ↔ JSON** | Transparent, gestion interne |

### ⚠️ Important

- Les modifications se font **en mémoire**, appeler `db.to_cbor()` pour sauvegarder
- Les clés de listes **doivent être spécifiées** dans les prédicats
- Les valeurs identityref doivent utiliser le **nom court** (pas le chemin complet)
- Une **copie profonde** est systématiquement utilisée pour éviter les corruptions

---

## Gestion des erreurs

### KeyError

```python
try:
    value = db["/invalid/path/that/does/not/exist"]
except KeyError as e:
    print(f"Chemin non trouvé: {e}")
```

### ValueError

```python
try:
    # Essayer d'utiliser des prédicats sans liste
    db["/simple_container[key='wrong']/value"]
except ValueError as e:
    print(f"Erreur de validation: {e}")
```

---

## Limites et considérations

1. **Structures plates et hiérarchiques supportées**
   - ✅ Listes simples avec clés uniques
   - ✅ Listes imbriquées (Containers A > Lists B > Lists C)
   - ✅ Containers sans listes

2. **Pas de support actuellement**
   - ❌ XPath fonctionnelles (positions, wildcards)
   - ❌ Chemins absolus sans racine
   - ❌ Prédicats multiples sur le même niveau (`..|..`)

---

## Exemples avancés

### Pattern: Mettre à jour tous les comptes d'échantillons

```python
# Lire tous les measurements
measurements = db["/measurements"]

# Parcourir et incrémenter chaque sample-count
for meas in measurements['measurement']:
    meas_type = meas['type']
    meas_id = meas['id']
    
    # Incrémenter
    db[f"/measurements/measurement[type='{meas_type}'][id='{meas_id}']/sample-count"] += 1
```

### Pattern: Créer une série d'entrées

```python
for i in range(5):
    xpath = f"/items/item[id='{i}']"
    # Écrire automatiquement crée l'entrée
    db[f"{xpath}/value"] = i * 100
    db[f"{xpath}/label"] = f"Item_{i}"
```

### Pattern: Nettoyer les données

```python
# Supprimer tous les champs 'debug' s'ils existent
for i in range(10):
    try:
        del db[f"/measurements/measurement[type='temp'][id='{i}']/debug"]
    except KeyError:
        pass  # Le champ n'existe pas, c'est ok
```

---

## Références

- [YANG RFC 6020](https://tools.ietf.org/html/rfc6020)
- [CORECONF RFC 9363](https://tools.ietf.org/html/rfc9363)
- [SID Assignment IANA](https://www.iana.org/)

