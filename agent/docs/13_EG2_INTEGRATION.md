# Intégration EG2

Le moteur de production est EG2 derrière `KnowledgeMemoryPort`. Les sources classées produisent des passages vectorisés par LM Studio ; SQLite conserve les passages, leurs vecteurs et leur provenance. Le LLM de génération reçoit ensuite les passages sélectionnés et cite les références P/V. Voir [moteur](20_EG2_ENGINE.md).
