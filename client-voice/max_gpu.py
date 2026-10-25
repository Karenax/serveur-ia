"""Stable Vulkan adapter identity and user selection, shared by Max engines."""
import hashlib


def gpu_id(item):
    # A PCI address survives backend enumeration changes. If unavailable, the
    # exact description/type identifies distinct adapters; ambiguity fails closed.
    identity='pci:'+item['pci_id'] if item.get('pci_id') else item['description']+'|'+item.get('kind','unknown')
    return hashlib.sha256(identity.encode()).hexdigest()[:24]


class GPUCompatibilityError(ValueError):
    code='gpu_unavailable'


def gpu_candidates(devices):
    return [item for item in devices if item['name'].startswith('Vulkan') and
            any(word in item['description'].lower() for word in ('nvidia','geforce','quadro','tesla','amd','radeon'))]


def select_gpu(devices,selection='auto'):
    """Prefer dedicated VRAM over shared RAM; never silently replace a manual choice."""
    cards=gpu_candidates(devices)
    if selection!='auto':
        matches=[item for item in cards if item.get('id',gpu_id(item))==selection]
        if len(matches)!=1:
            raise GPUCompatibilityError('La carte graphique choisie n’est plus identifiable. Actualisez les cartes et choisissez-la à nouveau. Aucune autre carte n’a été utilisée.')
        return matches[0]
    if not cards:
        raise GPUCompatibilityError('Le moteur Max ne détecte aucune carte AMD ou NVIDIA via Vulkan. Vérifiez le pilote graphique et mettez le complément Max à jour.')
    return max(cards,key=lambda item:({'dedicated':2,'integrated':0}.get(item.get('kind'),1),item.get('total_bytes',0),item.get('free_bytes',0)))
