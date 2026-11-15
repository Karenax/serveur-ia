(async () => {
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const pairing = await (await fetch(messenger.runtime.getURL("pairing.json"))).json();
  if (pairing.kiara) document.getElementById("instructions").append(" Gardez Kiara ouvert pendant la synchronisation.");
  const state = await messenger.storage.local.get(["folders", "connection"]);
  status.textContent = state.connection?.connected ? "Connecté à Agent." : "En attente de la connexion à Agent.";
  const accounts = await messenger.accounts.list(true);
  const visit = (account, folder) => {
    if ((folder.specialUse || []).some(x => ["trash", "junk", "drafts", "outbox", "templates"].includes(x)) || ["trash", "junk", "drafts", "outbox", "templates"].includes(folder.type)) return;
    if (!folder.isRoot && folder.id) {
      const label = document.createElement("label"); const input = document.createElement("input");
      input.type = "checkbox"; input.value = folder.id; input.checked = (state.folders || []).includes(folder.id);
      label.append(input, ` ${account.name} — ${folder.path || folder.name}`); document.getElementById("folders").append(label);
    }
    for (const child of folder.subFolders || []) visit(account, child);
  };
  for (const account of accounts) {
    const folders = account.rootFolder ? await messenger.folders.getSubFolders(account.rootFolder.id, true) : account.folders || [];
    for (const folder of folders) visit(account, folder);
  }
  save.disabled = false;
  save.addEventListener("click", async () => {
    save.disabled = true;
    status.textContent = "Enregistrement des dossiers…";
    try {
      const folders = Array.from(document.querySelectorAll("input:checked")).map(input => input.value);
      const result = await messenger.runtime.sendMessage({ action: "configure", folders });
      status.textContent = result?.accepted
        ? "Dossiers enregistrés. Synchronisation demandée."
        : `${result?.detail || "Impossible d’enregistrer les dossiers."} Vérifiez la liaison à Agent puis réessayez.`;
    } catch {
      status.textContent = "Impossible d’enregistrer les dossiers. Vérifiez la liaison à Agent puis réessayez.";
    } finally {
      save.disabled = false;
    }
  });
})().catch(() => {
  document.getElementById("status").textContent = "Impossible de charger les dossiers. Rouvrez les réglages de l’extension.";
});
