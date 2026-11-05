// toISOString() da la fecha en UTC: de noche ya sería el día siguiente. Estas usan el reloj del equipo.
const dosDigitos = (n) => String(n).padStart(2, '0');

export const aFechaLocal = (fecha = new Date()) =>
  `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`;

// Formato de un <input type="datetime-local">
export const aFechaHoraLocal = (fecha = new Date()) =>
  `${aFechaLocal(fecha)}T${dosDigitos(fecha.getHours())}:${dosDigitos(fecha.getMinutes())}`;

export const inicioDelDia = (fecha) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
export const finDelDia = (fecha) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate(), 23, 59, 59, 999);

// Límites de un periodo para la API, en instantes exactos
export const aPeriodoApi = (desde, hasta) => ({
  fecha_desde: inicioDelDia(desde).toISOString(),
  fecha_hasta: finDelDia(hasta).toISOString(),
});

export const periodoDelDia = (texto) => {
  const dia = new Date(`${texto}T00:00:00`);
  return aPeriodoApi(dia, dia);
};

export const periodoMesActual = (hoy = new Date()) =>
  aPeriodoApi(new Date(hoy.getFullYear(), hoy.getMonth(), 1), hoy);
