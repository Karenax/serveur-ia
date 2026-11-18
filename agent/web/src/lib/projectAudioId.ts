/** Namespace project recordings inside the existing, recoverable audio store. */
export const PROJECT_AUDIO_PREFIX = 'kiara-project-audio-v1:';

export function isProjectAudioSession(value: string): boolean {
  return typeof value === 'string' && value.startsWith(PROJECT_AUDIO_PREFIX);
}

export function projectAudioPrefix(operatorId: string, projectId: string): string {
  if (typeof operatorId !== 'string' || !operatorId || operatorId.length > 120 ||
      typeof projectId !== 'string' || !projectId || projectId.length > 36) {
    throw new Error('Projet ou compte audio invalide.');
  }
  return PROJECT_AUDIO_PREFIX + encodeURIComponent(operatorId) + ':' + encodeURIComponent(projectId) + ':';
}

export function projectAudioSession(operatorId: string, projectId: string, captureId: string): string {
  if (typeof captureId !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(captureId)) {
    throw new Error('Capture audio invalide.');
  }
  return projectAudioPrefix(operatorId, projectId) + captureId.toLowerCase();
}
