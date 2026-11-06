// Todos los equipos trabajan con la hora de la clínica, sin importar la zona configurada en cada uno.
// Un Date "de calendario" lleva en sus campos la fecha y hora de la clínica; no representa un instante.
const dosDigitos = (n) => String(n).padStart(2, '0');

const CLAVE_ZONA = 'zona_clinica';
let zona = null;

const zonaValida = (candidata) => {
  try {
    new Intl.DateTimeFormat([], { timeZone: candidata });
    return true;
  } catch {
    return false;
  }
};

export const fijarZonaClinica = (nueva) => {
  if (!nueva || !zonaValida(nueva)) return;
  zona = nueva;
  try {
    localStorage.setItem(CLAVE_ZONA, nueva);
  } catch {
    // Sin almacenamiento se vuelve a pedir en cada carga
  }
};

// Se llama antes de dibujar la aplicación: sin servidor, usa la última zona conocida
export const cargarZonaClinica = async () => {
  try {
    fijarZonaClinica(localStorage.getItem(CLAVE_ZONA));
  } catch {
    // Sin almacenamiento se espera la respuesta del servidor
  }
  try {
    const respuesta = await fetch('/api/v1/configuracion/publica');
    if (respuesta.ok) fijarZonaClinica((await respuesta.json()).zona_horaria);
  } catch {
    // Sin servidor la pantalla de acceso mostrará el error correspondiente
  }
};

const conZona = (opciones = {}) => (zona ? { ...opciones, timeZone: zona } : opciones);

const partesEnZona = (instante) => {
  const partes = new Intl.DateTimeFormat('en-US', conZona({
    year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric', hourCycle: 'h23',
  })).formatToParts(instante);
  const valor = (tipo) => Number(partes.find((p) => p.type === tipo).value);
  return { y: valor('year'), m: valor('month'), d: valor('day'), h: valor('hour'), mi: valor('minute'), s: valor('second') };
};

// Date de calendario con la fecha y hora actuales de la clínica
export const relojClinica = (instante = new Date()) => {
  const { y, m, d, h, mi, s } = partesEnZona(instante);
  return new Date(y, m - 1, d, h, mi, s);
};

// El instante real de una fecha y hora de la clínica. Dos pasadas: el desfase puede cambiar con el horario de verano.
const instanteClinica = (y, mes, d, h = 0, mi = 0, s = 0, ms = 0) => {
  const pedido = Date.UTC(y, mes, d, h, mi, s, ms);
  const desfase = (t) => {
    const p = partesEnZona(new Date(t));
    return Date.UTC(p.y, p.m - 1, p.d, p.h, p.mi, p.s) - Math.floor(t / 1000) * 1000;
  };
  const primero = pedido - desfase(pedido);
  return new Date(pedido - desfase(primero));
};

// Convierte el texto de un formulario, "AAAA-MM-DDTHH:MM", en el instante que entiende la API
export const aInstanteIso = (texto) => {
  const [y, m, d, h = 0, mi = 0, s = 0] = texto.split(/[-T:]/).map(Number);
  return instanteClinica(y, m - 1, d, h, mi, s).toISOString();
};

export const aFechaLocal = (fecha = relojClinica()) =>
  `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`;

// Formato de un <input type="datetime-local">
export const aFechaHoraLocal = (fecha = relojClinica()) =>
  `${aFechaLocal(fecha)}T${dosDigitos(fecha.getHours())}:${dosDigitos(fecha.getMinutes())}`;

export const inicioDelDia = (fecha) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
export const finDelDia = (fecha) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate(), 23, 59, 59, 999);

// Límites de un periodo de calendario para la API, en instantes exactos
export const aPeriodoApi = (desde, hasta) => ({
  fecha_desde: instanteClinica(desde.getFullYear(), desde.getMonth(), desde.getDate()).toISOString(),
  fecha_hasta: instanteClinica(hasta.getFullYear(), hasta.getMonth(), hasta.getDate(), 23, 59, 59, 999).toISOString(),
});

export const periodoDelDia = (texto) => {
  const dia = new Date(`${texto}T00:00:00`);
  return aPeriodoApi(dia, dia);
};

export const periodoMesActual = (hoy = relojClinica()) =>
  aPeriodoApi(new Date(hoy.getFullYear(), hoy.getMonth(), 1), hoy);

// Para mostrar un instante que viene de la API
export const verFechaHora = (valor, opciones) => new Date(valor).toLocaleString([], conZona(opciones));
export const verFecha = (valor, opciones) => new Date(valor).toLocaleDateString([], conZona(opciones));
export const verHora = (valor, opciones) => new Date(valor).toLocaleTimeString([], conZona(opciones));
