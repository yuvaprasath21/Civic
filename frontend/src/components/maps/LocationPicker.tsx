import { useCallback, useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import { LocateFixed } from "lucide-react";

const markerIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

interface LocationPickerProps {
  latitude: number | null;
  longitude: number | null;
  onChange: (lat: number, lng: number) => void;
  height?: number;
}

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click(e) { onPick(e.latlng.lat, e.latlng.lng); } });
  return null;
}

function RecenterOnChange({ latitude, longitude }: { latitude: number; longitude: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([latitude, longitude], map.getZoom());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latitude, longitude]);
  return null;
}

const DEFAULT_CENTER: [number, number] = [20.5937, 78.9629];

export function LocationPicker({ latitude, longitude, onChange, height = 320 }: LocationPickerProps) {
  const [isLocating, setIsLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);

  const useCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocateError("Your browser doesn't support geolocation.");
      return;
    }
    setIsLocating(true);
    setLocateError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onChange(position.coords.latitude, position.coords.longitude);
        setIsLocating(false);
      },
      () => {
        setLocateError("Couldn't get your location. Please select it on the map instead.");
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [onChange]);

  const center: [number, number] = latitude !== null && longitude !== null ? [latitude, longitude] : DEFAULT_CENTER;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-slate-500">Tap the map to set the exact location, or use your current position.</p>
        <button type="button" onClick={useCurrentLocation} disabled={isLocating}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700 disabled:opacity-60">
          <LocateFixed className="h-4 w-4" />
          {isLocating ? "Locating..." : "Use current location"}
        </button>
      </div>
      {locateError && <p className="text-sm text-red-600 mb-2">{locateError}</p>}
      <div style={{ height }} className="rounded-lg overflow-hidden border border-slate-300">
        <MapContainer center={center} zoom={latitude !== null ? 16 : 5} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickHandler onPick={onChange} />
          {latitude !== null && longitude !== null && (
            <>
              <Marker position={[latitude, longitude]} icon={markerIcon} />
              <RecenterOnChange latitude={latitude} longitude={longitude} />
            </>
          )}
        </MapContainer>
      </div>
      {latitude !== null && longitude !== null && (
        <p className="mt-2 text-xs text-slate-400">{latitude.toFixed(6)}, {longitude.toFixed(6)}</p>
      )}
    </div>
  );
}
