#!/usr/bin/env python3
"""Preprocesador de incidencias de tráfico de España para RainDrive Radar.

Baja los feeds DATEX II del Punto de Acceso Nacional (DGT v3.7, Servei Català de Trànsit, Tráfico del Gobierno Vasco),
los normaliza y los publica como JSON pequeño por celdas de 1° (tiles/<lat>_<lon>.json) más meta.json.
La app solo descarga las celdas que caen dentro de su radio de 50 km.

Reglas de seguridad de datos:
- Si una fuente falla, meta.json lo dice (ok=false) y NO se reutilizan datos antiguos de esa fuente: la app mostrará
  "datos de tráfico incompletos" y nunca "sin incidencias" para esa zona.
- Los registros sin coordenadas (solo puntos kilométricos o AlertC) se descartan y se cuentan en `skipped`.
"""
import datetime as dt
import io
import json
import math
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = {
    "dgt": "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml",
    "sct": "https://nap.dgt.es/datex2/sct/SituationPublication/all/content.xml",
    "dtgv": "https://nap.dgt.es/datex2/dt-gv/SituationPublication/all/content.xml",
}
USER_AGENT = "RainDriveTrafficFeed/1.0 (+datos abiertos NAP; proyecto sin ánimo de lucro)"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
FUTURE_LIMIT = dt.timedelta(hours=2)  # obras planificadas que empiezan más tarde no se muestran aún


def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_time(s):
    try:
        t = dt.datetime.fromisoformat(s.strip())
    except (ValueError, AttributeError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t


def collect(rec):
    """Recorre el registro y junta, por nombre local de elemento, los textos no vacíos; y los pares lat/lon."""
    texts = {}
    points = []
    comments = []
    for el in rec.iter():
        name = local(el.tag)
        if name == "pointCoordinates":
            lat = lon = None
            for ch in el:
                n = local(ch.tag)
                if n == "latitude":
                    lat = ch.text
                elif n == "longitude":
                    lon = ch.text
            try:
                la, lo = float(lat), float(lon)
                if -90 <= la <= 90 and -180 <= lo <= 180:
                    points.append((round(la, 5), round(lo, 5)))
            except (TypeError, ValueError):
                pass
        if name in ("comment", "generalPublicComment"):
            for v in el.iter():
                if local(v.tag) == "value" and v.text and v.text.strip():
                    comments.append(v.text.strip())
        t = (el.text or "").strip()
        if t:
            texts.setdefault(name, []).append(t)
    return texts, points, comments


def first(texts, *names):
    for n in names:
        if texts.get(n):
            return texts[n][0]
    return None


def classify(type_name, texts):
    """Devuelve (categoría, subtipo, gravedad 0..3). Categorías: accident, closure, congestion, works,
    obstruction, weather, restriction, other."""
    tokens = set()
    for n in ("causeType", "roadMaintenanceType", "roadOrCarriagewayOrLaneManagementType", "effectOnRoadLayout",
              "abnormalTrafficType", "accidentType", "obstructionType", "poorEnvironmentType",
              "constructionWorkType", "speedManagementType", "genericSituationRecordName", "detailedCauseType"):
        for v in texts.get(n, []):
            tokens.add(v.lower())
    impact = (first(texts, "impactOnTraffic") or "").lower()
    sev = (first(texts, "severity", "overallSeverity") or "").lower()
    sub = (first(texts, "roadOrCarriagewayOrLaneManagementType", "accidentType", "abnormalTrafficType",
                 "obstructionType", "poorEnvironmentType", "speedManagementType", "roadMaintenanceType",
                 "constructionWorkType", "causeType", "genericSituationRecordName") or type_name)
    if type_name == "Accident" or "accident" in tokens or texts.get("accidentType"):
        cat = "accident"
    elif {"roadclosed", "carriagewayclosures"} & tokens or impact == "impossible":
        cat = "closure"
    elif type_name == "AbnormalTraffic" or texts.get("abnormalTrafficType"):
        cat = "congestion"
    elif type_name in ("MaintenanceWorks", "ConstructionWorks") or {"roadworks", "constructionwork",
                                                                    "maintenancework", "resurfacingwork"} & tokens:
        cat = "works"
    elif type_name == "SpeedManagement":
        cat = "restriction"
    elif type_name == "PoorEnvironmentConditions":
        cat = "weather"
    elif type_name in ("GeneralObstruction", "VehicleObstruction", "AnimalPresenceObstruction",
                       "EnvironmentalObstruction", "GenericSituationRecord") or "obstruction" in tokens:
        cat = "obstruction"
    elif type_name == "RoadOrCarriagewayOrLaneManagement":
        cat = "restriction"
    else:
        cat = "other"
    base = {"closure": 3, "accident": 3, "congestion": 2, "obstruction": 2, "weather": 1, "works": 1,
            "restriction": 1, "other": 1}[cat]
    if sev in ("high", "highest") or impact in ("heavy", "congested"):
        base = min(3, base + 1)
    if impact == "impossible":
        base = 3
    if cat == "restriction" and base > 2:
        base = 2
    return cat, sub, base


def parse_feed(xml_bytes, source, now):
    """Devuelve (incidencias, publicationTime|None, descartadas)."""
    incidents, skipped, pub_time = [], 0, None
    for _, el in ET.iterparse(io.BytesIO(xml_bytes), events=("end",)):
        name = local(el.tag)
        if name == "publicationTime" and pub_time is None:
            pub_time = parse_time(el.text or "")
        if name != "situation":
            continue
        sit_id = el.get("id") or "?"
        status = ""
        for ch in el.iter():
            if local(ch.tag) == "informationStatus":
                status = (ch.text or "").strip().lower()
        sit_sev = ""
        for ch in el:
            if local(ch.tag) == "overallSeverity":
                sit_sev = (ch.text or "").strip()
        for rec in el:
            if local(rec.tag) != "situationRecord":
                continue
            if status == "test":
                continue
            type_name = local(rec.get(XSI_TYPE, "")).split(":")[-1] or "Unknown"
            texts, points, comments = collect(rec)
            if sit_sev and "severity" not in texts:
                texts["overallSeverity"] = [sit_sev]
            vstatus = (first(texts, "validityStatus") or "").lower()
            start, end = parse_time(first(texts, "overallStartTime")), parse_time(first(texts, "overallEndTime"))
            if vstatus == "suspended" or (end and end < now) or (start and start > now + FUTURE_LIMIT):
                continue
            # puntos distintos en orden de aparición
            uniq = []
            for p in points:
                if p not in uniq:
                    uniq.append(p)
            if not uniq:
                skipped += 1
                continue
            cat, sub, sev = classify(type_name, texts)
            km = first(texts, "kilometerPoint")
            if km is None and first(texts, "referencePointDistance"):
                try:
                    km = float(first(texts, "referencePointDistance")) / 1000.0
                except ValueError:
                    km = None
            else:
                try:
                    km = float(km) if km is not None else None
                except ValueError:
                    km = None
            limit = first(texts, "temporarySpeedLimit")
            incidents.append({
                "i": f"{source}:{sit_id}:{rec.get('id') or ''}",
                "c": cat, "y": sub, "s": sev,
                "p": list(uniq[0]), "q": list(uniq[-1]) if len(uniq) > 1 else None,
                "r": first(texts, "roadName", "roadNumber"),
                "k": round(km, 1) if km is not None else None,
                "d": first(texts, "tpegDirection", "directionRelative"),
                "u": first(texts, "municipality"),
                "t": (comments[0][:160] if comments else None),
                "v": limit,
                "e": end.isoformat() if end else None,
                "src": source,
            })
        el.clear()
    return incidents, pub_time, skipped


def tiles_for(inc):
    lats = [inc["p"][0]] + ([inc["q"][0]] if inc["q"] else [])
    lons = [inc["p"][1]] + ([inc["q"][1]] if inc["q"] else [])
    for la in range(math.floor(min(lats)), math.floor(max(lats)) + 1):
        for lo in range(math.floor(min(lons)), math.floor(max(lons)) + 1):
            yield la, lo


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def build(out_dir, now=None, fetcher=fetch, sources=SOURCES):
    now = now or dt.datetime.now(dt.timezone.utc)
    meta = {"schema": 1, "generatedAt": now.isoformat(), "sources": {}}
    tiles = {}
    for name, url in sources.items():
        try:
            data = fetcher(url)
            incs, pub, skipped = parse_feed(data, name, now)
            meta["sources"][name] = {"ok": True, "publicationTime": pub.isoformat() if pub else None,
                                     "incidents": len(incs), "skipped": skipped}
            for inc in incs:
                for key in tiles_for(inc):
                    tiles.setdefault(key, []).append(inc)
        except Exception as e:  # una fuente caída no tumba las demás
            meta["sources"][name] = {"ok": False, "error": type(e).__name__}
            print(f"[{name}] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
    tdir = os.path.join(out_dir, "tiles")
    os.makedirs(tdir, exist_ok=True)
    for f in os.listdir(tdir):
        os.remove(os.path.join(tdir, f))
    for (la, lo), incs in tiles.items():
        with open(os.path.join(tdir, f"{la}_{lo}.json"), "w", encoding="utf-8") as f:
            json.dump(incs, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
    return meta


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    m = build(out)
    print(json.dumps(m, ensure_ascii=False))
    # Si NINGUNA fuente respondió, el trabajo falla (no se publica un meta vacío encima del anterior).
    sys.exit(0 if any(s["ok"] for s in m["sources"].values()) else 1)
