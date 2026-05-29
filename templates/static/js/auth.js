/* ═══ MASCATE — AUTH JS ═══ */

const API = window.location.origin;
let selectedRole = null;

const EYE_OPEN   = '<svg width="17" height="17"><use href="#eye-open"/></svg>';
const EYE_CLOSED = '<svg width="17" height="17"><use href="#eye-closed"/></svg>';

// Cargar dispositivos para el select de prescriptor
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch(API + '/dispositivos/');
    const disps = await res.json();
    const sel = document.getElementById('regPrescDisp');
    sel.innerHTML = '<option value="">Selecciona dispositivo...</option>';
    disps.forEach(d => { sel.innerHTML += `<option value="${d.id}">${d.nombre}</option>`; });
  } catch(e) { console.log('Sin conexion al backend'); }
});

function switchTab(tab) {
  document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
  document.getElementById('tabReg').classList.toggle('active', tab === 'register');
  document.getElementById('loginView').style.display    = tab === 'login'    ? 'block' : 'none';
  document.getElementById('registerView').style.display = tab === 'register' ? 'block' : 'none';
  document.getElementById('successView').classList.remove('visible');
  document.getElementById('successView').style.display = '';
}

function selectRole(role) {
  selectedRole = role;
  document.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('role-' + role).classList.add('selected');
  document.querySelectorAll('.dynamic-fields').forEach(f => f.classList.remove('visible'));
  document.getElementById('fields-' + role).classList.add('visible');
  document.getElementById('submitWrap').style.display = 'block';
}

function togglePw(id, btn) {
  const inp = document.getElementById(id);
  const isPassword = inp.type === 'password';
  inp.type = isPassword ? 'text' : 'password';
  btn.innerHTML = isPassword ? EYE_CLOSED : EYE_OPEN;
}

function showToast(msg, isError) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast' + (isError ? ' error' : '') + ' show';
  setTimeout(() => t.classList.remove('show'), 3000);
}

function val(id) { return document.getElementById(id)?.value?.trim() ?? ''; }

async function doLogin() {
  const email = val('loginEmail');
  const pw    = document.getElementById('loginPw').value;
  if (!email || !pw) { showToast('Por favor completa todos los campos', true); return; }
  if (!/\S+@\S+\.\S+/.test(email)) { showToast('Correo no valido', true); return; }
  showToast('Verificando credenciales...');
  try {
    const res = await fetch(API + '/auth/login', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ email, password: pw })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Credenciales incorrectas', true); return; }
    localStorage.setItem('mascate_token', data.access_token);
    localStorage.setItem('mascate_rol', data.rol);
    localStorage.setItem('mascate_nombre', data.nombre);
    localStorage.setItem('mascate_email', email);
    showToast('Bienvenidx, ' + data.nombre + '!');
    setTimeout(() => { window.location.href = '/dashboard'; }, 800);
  } catch(e) {
    showToast('Error de conexion con el servidor', true);
  }
}

// Campos requeridos por rol
const ROL_FIELDS = {
  dispositivo: {
    email:            'regDispEmail',
    password:         'p1',
    nombre:           'regDispNombre',
    lugar_actividades:'regDispLugar',
    ubicacion:        'regDispUbicacion',
    tipo_servicio:    'regDispTipo',
    dia_actividad:    'regDispDia',
    hora_actividad:   'regDispHora',
    telefono:         'regDispTel',
    redes_sociales:   'regDispRedes',
  },
  prescriptor: {
    email:             'regPrescEmail',
    password:          'p2',
    nombre_completo:   'regPrescNombre',
    perfil_disciplina: 'regPrescDisciplina',
    telefono:          'regPrescTel',
    _dispositivo_id:   'regPrescDisp',   // prefijo _ = tratamiento especial
  },
  beneficiario: {
    email:       'regBenefEmail',
    password:    'p4',
    nombre_apodo:'regBenefNombre',
  },
};

// Validaciones mínimas por rol
const ROL_REQUIRED = {
  dispositivo:  { field: 'nombre',           msg: 'Ingresa el nombre del dispositivo' },
  prescriptor:  { field: 'nombre_completo',  msg: 'Ingresa tu nombre completo' },
  beneficiario: { field: 'nombre_apodo',     msg: 'Ingresa tu nombre o apodo' },
};

async function doRegister() {
  if (!selectedRole) { showToast('Elige un rol primero', true); return; }
  const mapping = ROL_FIELDS[selectedRole];
  const p = { rol: selectedRole };

  for (const [key, id] of Object.entries(mapping)) {
    if (key === '_dispositivo_id') {
      const did = document.getElementById(id).value;
      if (did) p.dispositivo_id = parseInt(did);
    } else {
      p[key] = document.getElementById(id).value.trim();
    }
  }

  // Validación específica del rol
  const req = ROL_REQUIRED[selectedRole];
  if (req && !p[req.field]) { showToast(req.msg, true); return; }
  if (!p.email || !p.password) { showToast('Completa correo y contraseña', true); return; }

  showToast('Creando tu cuenta...');
  try {
    const res = await fetch(API + '/auth/register', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(p)
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Error al registrar', true); return; }
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('registerView').style.display = 'none';
    const sv = document.getElementById('successView');
    sv.style.display = 'flex'; sv.classList.add('visible');
  } catch(e) {
    showToast('Error de conexion con el servidor', true);
  }
}

function goToLogin() {
  document.getElementById('successView').classList.remove('visible');
  document.getElementById('successView').style.display = 'none';
  switchTab('login');
}
