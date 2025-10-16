import { useEffect, useState } from "react";
import './nightvision.css';

function App() {
  const [catalog, setCatalog] = useState([]);
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [trackingList, setTrackingList] = useState(() => {
    const saved = localStorage.getItem("trackingList");
    return saved ? JSON.parse(saved) : [];
  });
  const [location, setLocation] = useState(null);

  // 🕒 Observing time persistence
  const [useNow, setUseNow] = useState(() => {
    const saved = localStorage.getItem("useNow");
    return saved ? JSON.parse(saved) : true;
  });
  const [customTime, setCustomTime] = useState(() => {
    return localStorage.getItem("customTime") || "";
  });
  const [observingDate, setObservingDate] = useState(() => {
    const saved = localStorage.getItem("observingDate");
    return saved ? new Date(saved) : new Date();
  });

  // ℹ️ Info modal
  const [infoData, setInfoData] = useState(null);

  // Save tracking list persistently
  useEffect(() => {
    localStorage.setItem("trackingList", JSON.stringify(trackingList));
  }, [trackingList]);

  // Save observing time persistently
  useEffect(() => {
    localStorage.setItem("useNow", JSON.stringify(useNow));
    localStorage.setItem("customTime", customTime);
    localStorage.setItem("observingDate", observingDate.toISOString());
  }, [useNow, customTime, observingDate]);

  function formatHAM(hoursDecimal) {
    const hours = Math.floor(Math.abs(hoursDecimal));
    const minutes = Math.floor((Math.abs(hoursDecimal) - hours) * 60);
    return `${hours}h ${minutes}m`;
  }

  const API_BASE = "";

  // Fetch catalog once and get location
  useEffect(() => {
    fetch(`${API_BASE}/catalog`)
      .then((res) => res.json())
      .then((json) => {
        console.log("📥 Catalog loaded:", json);
        setCatalog(json);
      })
      .catch((err) => console.error("❌ Catalog fetch error:", err));

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
      });
    }
  }, []);

  // 🔄 Update HA/Alt
  useEffect(() => {
    if (!location || trackingList.length === 0) return;

    const interval = setInterval(() => {
      const now = new Date();
      const currentDate = useNow ? now : observingDate;

      const updatedList = trackingList.map((obj) => {
        if (!obj.ra_deg || !obj.dec_deg) return obj;

        const LST = getLST(currentDate, location.lon); // hours
        const RA_hours = obj.ra_deg / 15.0;
        let HA = LST - RA_hours;
        if (HA > 12) HA -= 24;
        if (HA < -12) HA += 24;

        const haSign = HA >= 0 ? "W" : "E";
        const haFormatted = formatHAM(HA);

        const HA_rad = (HA * 15 * Math.PI) / 180;
        const decRad = (obj.dec_deg * Math.PI) / 180;
        const latRad = (location.lat * Math.PI) / 180;

        const sinAlt =
          Math.sin(decRad) * Math.sin(latRad) +
          Math.cos(decRad) * Math.cos(latRad) * Math.cos(HA_rad);
        const altDeg = Math.asin(sinAlt) * (180 / Math.PI);

        return {
          ...obj,
          ha: `${haFormatted} ${haSign}`,
          alt: altDeg.toFixed(2) + "°",
        };
      });

      setTrackingList(updatedList);
    }, 1000);

    return () => clearInterval(interval);
  }, [location, trackingList, useNow, observingDate]);

  // --- Handlers for observing time ---
  const handleUpdateTime = () => {
    if (customTime) {
      setObservingDate(new Date(customTime));
      setUseNow(false);
    }
  };

  const handleResetTime = () => {
    setUseNow(true);
    setObservingDate(new Date());
    setCustomTime("");
  };

  // Handle typing/search
  const handleChange = (event) => {
    const value = event.target.value;
    setQuery(value);

    if (value.length > 0 && catalog.length > 0) {
      const valueLower = value.toLowerCase();
      const filtered = catalog.filter((obj) => {
        const id = obj["object ID"] ?? "";
        const name = obj.name ?? "";
        const ngc = obj.NGC ?? "";
        return (
          id.toLowerCase().includes(valueLower) ||
          name.toLowerCase().includes(valueLower) ||
          ngc.toLowerCase().includes(valueLower)
        );
      });

      setSuggestions(filtered);
    } else {
      setSuggestions([]);
    }
  };

  // Handle selecting a target
  const handleSelect = (obj) => {
    setQuery("");
    setSuggestions([]);

    const targetId = obj["object ID"] || obj.NGC || obj.name;

    if (!location) {
      alert("Waiting for location...");
      return;
    }

    fetch(
      `${API_BASE}/target/${encodeURIComponent(
        targetId
      )}?lat=${location.lat}&lon=${location.lon}`
    )
      .then((res) => res.json())
      .then((json) => {
        const newObj = {
  id: targetId,
  name: json.name || obj.name,
  ra_deg: json.ra_deg,
  dec_deg: json.dec_deg,
  dec: json.dec,
  ha: "--",
  alt: "--",
  max_altitude_deg: json.max_altitude_deg?.toFixed(1) + "°" || "--",
  transit_time_local: json.transit_time_local || "--",  // 👈 fix here
};
        setTrackingList((prev) => [...prev, newObj]);
      })
      .catch((err) => console.error("❌ Target fetch error:", err));
  };

  const handleRemove = (index) => {
    setTrackingList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleShowInfo = (objId) => {
    const match = catalog.find(
      (c) => c["object ID"] === objId || c.NGC === objId || c.name === objId
    );
    if (match) {
      setInfoData({
        name: match.name,
        constellation: match.constellation,
        magnitude: match.magnitude,
        size: match.size,
        distance: match.distance,
        age: match.age,
        stars: match.Stars,
      });
    }
  };

  const handleCloseInfo = () => setInfoData(null);

  return (
    <div className="night-box" style={{ minHeight: "100vh", textAlign: "center", padding: "2rem" }}>
      <h1 style={{ color: "#ff2a2a", marginBottom: "1rem" }}>Astronomy Target Tracker</h1>

      {/* Observing time controls */}
      <div style={{ marginBottom: "1.5rem" }}>
        <input
          type="datetime-local"
          value={customTime}
          onChange={(e) => setCustomTime(e.target.value)}
          style={{ padding: "0.25rem", marginRight: "0.5rem" }}
        />
        <button
          onClick={handleUpdateTime}
          className="night-box"
          style={{ marginRight: "0.5rem" }}
        >
          Update
        </button>
        <button onClick={handleResetTime} className="night-box">
          Reset to Now
        </button>
        <p style={{ marginTop: "0.5rem", color: "#ff5555" }}>
          Current observing time: {observingDate.toLocaleString()} {useNow ? "(live)" : ""}
        </p>
      </div>

      {/* Search box */}
      <div style={{ position: "relative", width: "16rem", margin: "0 auto 1.5rem auto" }}>
        <input
          type="text"
          value={query}
          onChange={handleChange}
          className="night-box"
          style={{ width: "100%", padding: "0.5rem", borderRadius: "0.25rem" }}
          placeholder="Search catalog..."
        />
        {suggestions.length > 0 && (
          <ul className="night-list" style={{ position: "absolute", left: 0, right: 0, borderRadius: "0.25rem", maxHeight: "10rem", overflowY: "auto", zIndex: 10, marginTop: "0.25rem" }}>
            {suggestions.map((obj) => {
              const keyId = obj["object ID"] || obj.NGC || obj.name;
              return (
                <li key={keyId} style={{ padding: "0.5rem", cursor: "pointer" }} onClick={() => handleSelect(obj)}>
                  <span style={{ color: "#ff5555" }}>{obj["object ID"]}</span> – {obj.name}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Tracking List */}
      {trackingList.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          {trackingList.map((obj, index) => (
            <div key={index} className="night-box" style={{ padding: "0.5rem", marginBottom: "0.5rem", borderRadius: "0.25rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "1rem", alignItems: "center" }}>
                <div>
                  <p>
                    <strong style={{ color: "#ff5555" }}>{obj.name}</strong> <span style={{ color: "#ff2a2a" }}>({obj.id})</span>
                  </p>
                  <p><strong>Altitude:</strong> {obj.alt}</p>
                  <p><strong>Max Altitude:</strong> {obj.max_altitude_deg}</p>
                  <p>
  <strong>Transit Time:</strong>{" "}
  {obj.transit_time_local
  ? new Date(obj.transit_time_local).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true })
  : "--"}
</p>
                </div>
                <div>
                  <p><strong>DEC:</strong> {obj.dec}</p>
                  <p><strong>HA:</strong> {obj.ha}</p>
                </div>
                <div>
                  <button onClick={() => handleShowInfo(obj.id)} className="night-box" style={{ marginRight: "0.5rem" }}>ℹ️ Info</button>
                  <button
                    onClick={() => handleRemove(index)}
                    className="night-box"
                    style={{ background: "#a00", color: "#fff", padding: "0.25rem 0.5rem", borderRadius: "0.25rem", border: "none", cursor: "pointer" }}
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Modal */}
      {infoData && (
        <div className="modal-overlay" style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={handleCloseInfo}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ background: "#111", border: "1px solid #666", padding: "20px", borderRadius: "8px", color: "#0f0", maxWidth: "400px", width: "90%", position: "relative", textAlign: "center" }}>
            <button onClick={handleCloseInfo} style={{ position: "absolute", top: "8px", right: "8px", background: "transparent", border: "none", fontSize: "1.2rem", color: "#ff5555", cursor: "pointer" }}>×</button>
            <h3>{infoData.name}</h3>
            <p><strong>Constellation:</strong> {infoData.constellation}</p>
            <p><strong>Magnitude:</strong> {infoData.magnitude}</p>
            <p><strong>Size:</strong> {infoData.size}</p>
            <p><strong>Distance:</strong> {infoData.distance} ly</p>
            <p><strong>Age:</strong> {infoData.age}</p>
            <p><strong>Stars:</strong> {infoData.stars}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Helper: compute LST in hours ---
function getLST(date, longitude) {
  const JD = date.getTime() / 86400000 + 2440587.5;
  const D = JD - 2451545.0;
  let GMST = 18.697374558 + 24.06570982441908 * D;
  GMST = ((GMST % 24) + 24) % 24;
  let LST = GMST + longitude / 15.0;
  return ((LST % 24) + 24) % 24;
}

export default App;
