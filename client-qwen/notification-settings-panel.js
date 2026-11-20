'use strict';

const form = notificationPreferencesForm();
form.hidden = true;
document.querySelector('main').append(form);
const feedback = document.getElementById('notification-load');
const retry = document.getElementById('notification-retry');
const config = JSON.parse(document.getElementById('settings-config').textContent);

async function request(body) {
  const headers = {'Content-Type':'application/json'};
  if (config.key) headers.Authorization = 'Bearer '+config.key;
  const response = await fetch(config.prefix+'/v1/notifications/action',{
    method:'POST',headers,body:JSON.stringify(body),signal:AbortSignal.timeout(15000),
  });
  const data = await response.json();
  if (!response.ok) throw Object.assign(new Error(data.error?.message || data.detail || 'Action refusée.'),{status:response.status});
  return data;
}

async function load() {
  retry.hidden = true;
  feedback.textContent = 'Chargement des préférences…';
  try {
    const data = await request({action:'list',after:0,limit:1});
    preferences.apply(data.preferences);
    feedback.textContent = '';
    form.hidden = false;
  } catch (failure) {
    feedback.textContent = 'Chargement indisponible. '+failure.message;
    retry.hidden = false;
  }
}

const preferences = notificationPreferences(form,request,load,true);
retry.onclick = load;
window.kiaraShowDeviceSetting = section => section === 'notifications';
let theme = null;
try {theme = localStorage.getItem('fred-theme') || localStorage.getItem('agent-ui-theme');} catch {}
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
const setTheme = () => {document.documentElement.dataset.theme = theme === 'system' ? (systemTheme.matches ? 'dark' : 'light') : theme || 'light';};
setTheme();
systemTheme.addEventListener('change',setTheme);
window.addEventListener('storage',event => {
  if (event.key === 'fred-theme') {theme = event.newValue;setTheme();}
});
void load();
