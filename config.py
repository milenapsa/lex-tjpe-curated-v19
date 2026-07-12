import os
PORT=int(os.getenv("PORT","8080"))
UPSTREAM=os.getenv("LEX_UPSTREAM","http://homosapiens-lex-runtime-governance-v18:8080").rstrip("/")
VERSION="0.19.0-tjpe-curated"
UA="Lex-HomoSapiens/0.19"
TTL=1800
PAGE="https://portal.tjpe.jus.br/servicos/consulta/sumulas"
TRIBUNAL="https://portal.tjpe.jus.br/documents/10180/0/-/3b00bf2c-3a6a-8e76-0315-da03cb32145f"
ADMIN="https://portal.tjpe.jus.br/documents/10180/0/-/90bbec0a-acf7-b580-6bac-884a90d8682b"
PORTAL="https://portal.tjpe.jus.br/servicos/consulta/jurisprudencia"
