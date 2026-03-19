export const DEVICE_CLASS_COLORS = {
  phone: "#4fc3f7",
  car: "#ffb74d",
  headphones: "#ce93d8",
  laptop: "#80cbc4",
  tablet: "#80deea",
  tag: "#fff176",
  airtag: "#fff176",
  speaker: "#a5d6a7",
  wearable: "#f48fb1",
  unknown: "#9e9e9e",
};

export function macToAngle(mac) {
  const normalized = String(mac || "").replace(/[^0-9A-F]/gi, "").toUpperCase();
  if (!normalized) {
    return 0;
  }

  let hash = 0;
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash * 31 + normalized.charCodeAt(index)) % 3600;
  }

  return (hash / 3600) * Math.PI * 2;
}

export function getDeviceClassColor(deviceClass) {
  return DEVICE_CLASS_COLORS[deviceClass] || DEVICE_CLASS_COLORS.unknown;
}
