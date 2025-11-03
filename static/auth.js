// Простой фронтенд для теста регистрации/верификации/входа
function el(id){return document.getElementById(id)}

async function postJSON(url, data){
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
  return res;
}

el('btnRegister').addEventListener('click', async ()=>{
  const login = el('regLogin').value.trim();
  const password = el('regPassword').value;
  el('regResult').textContent = '';
  if(!login || !password){ el('regResult').textContent = 'Заполните поля'; return }

  const r = await postJSON('/register', {login, password});
  const j = await r.json().catch(()=>null);
  console.log('/register response', r.status, j);
  if(r.ok){
    el('regResult').textContent = 'Регистрация успешна. Выполните вход.';
    el('regResult').className='success';
  } else {
    el('regResult').textContent = (j && (j.error || j.detail)) || 'Ошибка'; el('regResult').className='error';
  }
});

// verification removed

el('btnLogin').addEventListener('click', async ()=>{
  const login = el('loginLogin').value.trim();
  const password = el('loginPassword').value;
  el('loginResult').textContent='';
  if(!login || !password){ el('loginResult').textContent='Заполните поля'; return }
  const r = await postJSON('/login', {login, password});
  if(r.ok){ el('loginResult').textContent='Вход выполнен'; el('loginResult').className='success'; showAccount(login); }
  else { const j = await r.json().catch(()=>({})); el('loginResult').textContent = j.error || 'Ошибка входа'; el('loginResult').className='error'; }
});

el('btnLogout').addEventListener('click', async ()=>{
  const r = await postJSON('/logout', {});
  if(r.ok){ hideAccount(); }
});

function showAccount(login){
  el('accountLogin').textContent = login;
  el('accountBlock').classList.remove('hidden');
}
function hideAccount(){
  el('accountBlock').classList.add('hidden');
}

function playAnim(){
  const box = document.querySelector('.box');
  box.classList.add('anim','play');
  setTimeout(()=> box.classList.remove('play'), 900);
}
