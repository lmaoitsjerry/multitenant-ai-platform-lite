// Shared IATA destination mapping for common travel destinations
export const DESTINATION_IATA = {
  zanzibar: 'ZNZ',
  mauritius: 'MRU',
  maldives: 'MLE',
  seychelles: 'SEZ',
  'cape town': 'CPT',
  'cape-town': 'CPT',
  durban: 'DUR',
  bali: 'DPS',
  phuket: 'HKT',
  dubai: 'DXB',
  nairobi: 'NBO',
  kenya: 'NBO',
  'victoria-falls': 'VFA',
  'dar-es-salaam': 'DAR',
  maputo: 'MPM',
  windhoek: 'WDH',
};

export function getDestinationIata(destination) {
  if (!destination) return '';
  // If it's already a 3-letter IATA code, return as-is
  if (/^[A-Z]{3}$/.test(destination.toUpperCase())) return destination.toUpperCase();
  return DESTINATION_IATA[destination.toLowerCase()] || destination.toUpperCase();
}
