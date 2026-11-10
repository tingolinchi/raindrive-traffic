import datetime as dt
import json
import os
import tempfile
import unittest

import build_traffic as bt

NOW = dt.datetime(2026, 11, 10, 15, 0, tzinfo=dt.timezone.utc)

V37 = b"""<?xml version="1.0" encoding="UTF-8"?>
<d2:payload xmlns:d2="http://datex2.eu/schema/3/d2Payload" xmlns:sit="http://datex2.eu/schema/3/situation"
  xmlns:com="http://datex2.eu/schema/3/common" xmlns:loc="http://datex2.eu/schema/3/locationReferencing"
  xmlns:lse="http://dgt.es/lse" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="sit:SituationPublication">
 <com:publicationTime>2026-11-10T15:59:00.000+01:00</com:publicationTime>
 <sit:situation id="S1"><sit:headerInformation><com:informationStatus>real</com:informationStatus></sit:headerInformation>
  <sit:overallSeverity>highest</sit:overallSeverity>
  <sit:situationRecord xsi:type="sit:RoadOrCarriagewayOrLaneManagement" id="R1">
   <sit:validity><com:validityStatus>active</com:validityStatus><com:overallStartTime>2026-09-30T13:43:12+02:00</com:overallStartTime></sit:validity>
   <sit:cause><sit:causeType>infrastructureDamageObstruction</sit:causeType></sit:cause>
   <sit:locationReference xsi:type="loc:PointLocation"><loc:tpegPointLocation><loc:point><loc:pointCoordinates>
     <loc:latitude>41.705166</loc:latitude><loc:longitude>-0.025548847</loc:longitude></loc:pointCoordinates></loc:point></loc:tpegPointLocation></sit:locationReference>
   <loc:roadName>HU-883</loc:roadName>
   <sit:roadOrCarriagewayOrLaneManagementType>roadClosed</sit:roadOrCarriagewayOrLaneManagementType>
  </sit:situationRecord></sit:situation>
 <sit:situation id="S2"><sit:headerInformation><com:informationStatus>real</com:informationStatus></sit:headerInformation>
  <sit:situationRecord xsi:type="sit:RoadOrCarriagewayOrLaneManagement" id="R2">
   <sit:validity><com:validityStatus>active</com:validityStatus><com:overallStartTime>2026-11-09T20:00:00+01:00</com:overallStartTime><com:overallEndTime>2027-02-26T19:00:00+01:00</com:overallEndTime></sit:validity>
   <sit:cause><sit:causeType>roadMaintenance</sit:causeType><sit:detailedCauseType><sit:roadMaintenanceType>roadworks</sit:roadMaintenanceType></sit:detailedCauseType></sit:cause>
   <sit:locationReference xsi:type="loc:SingleRoadLinearLocation">
     <loc:from><loc:pointCoordinates><loc:latitude>36.75545</loc:latitude><loc:longitude>-3.130541</loc:longitude></loc:pointCoordinates></loc:from>
     <loc:to><loc:pointCoordinates><loc:latitude>36.86577</loc:latitude><loc:longitude>-2.2701068</loc:longitude></loc:pointCoordinates></loc:to>
     <loc:roadName>A-7</loc:roadName><lse:kilometerPoint>802.5</lse:kilometerPoint><loc:tpegDirection>eastBound</loc:tpegDirection>
   </sit:locationReference>
   <sit:roadOrCarriagewayOrLaneManagementType>narrowLanes</sit:roadOrCarriagewayOrLaneManagementType>
  </sit:situationRecord></sit:situation>
 <sit:situation id="S3"><sit:headerInformation><com:informationStatus>real</com:informationStatus></sit:headerInformation>
  <sit:situationRecord xsi:type="sit:GenericSituationRecord" id="R3">
   <sit:validity><com:validityStatus>active</com:validityStatus><com:overallStartTime>2026-11-10T15:00:00+01:00</com:overallStartTime></sit:validity>
   <sit:cause><sit:causeType>accident</sit:causeType></sit:cause>
   <sit:locationReference xsi:type="loc:PointLocation"><loc:pointCoordinates><loc:latitude>39.47802</loc:latitude><loc:longitude>-0.42712465</loc:longitude></loc:pointCoordinates><loc:roadName>V-30</loc:roadName></sit:locationReference>
   <sit:generalPublicComment><sit:comment><com:values><com:value lang="es">Accidente a la altura del hotel</com:value></com:values></sit:comment></sit:generalPublicComment>
  </sit:situationRecord></sit:situation>
 <sit:situation id="S4"><sit:headerInformation><com:informationStatus>real</com:informationStatus></sit:headerInformation>
  <sit:situationRecord xsi:type="sit:SpeedManagement" id="R4">
   <sit:validity><com:validityStatus>active</com:validityStatus><com:overallEndTime>2026-11-01T13:00:00+01:00</com:overallEndTime></sit:validity>
   <sit:locationReference xsi:type="loc:PointLocation"><loc:pointCoordinates><loc:latitude>38.0</loc:latitude><loc:longitude>-1.0</loc:longitude></loc:pointCoordinates></sit:locationReference>
   <sit:speedManagementType>speedRestrictionInOperation</sit:speedManagementType><sit:temporarySpeedLimit>40.0</sit:temporarySpeedLimit>
  </sit:situationRecord></sit:situation>
 <sit:situation id="S5"><sit:headerInformation><com:informationStatus>real</com:informationStatus></sit:headerInformation>
  <sit:situationRecord xsi:type="sit:PoorEnvironmentConditions" id="R5">
   <sit:validity><com:validityStatus>active</com:validityStatus></sit:validity>
   <sit:locationReference xsi:type="loc:SingleRoadLinearLocation"><loc:roadName>A-8</loc:roadName></sit:locationReference>
   <sit:poorEnvironmentType>strongWinds</sit:poorEnvironmentType>
  </sit:situationRecord></sit:situation>
</d2:payload>"""

V1 = b"""<?xml version="1.0"?>
<_0:d2LogicalModel xmlns:_0="http://datex2.eu/schema/1_0/1_0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <_0:payloadPublication xsi:type="_0:SituationPublication" lang="es"><_0:publicationTime>2026-11-10T16:55:18.848+01:00</_0:publicationTime>
  <_0:situation id="GUID_1"><_0:headerInformation><_0:informationStatus>real</_0:informationStatus></_0:headerInformation>
   <_0:situationRecord xsi:type="_0:ConstructionWorks" id="GUID_1_sr">
    <_0:validity><_0:validityStatus>active</_0:validityStatus><_0:validityTimeSpecification><_0:overallStartTime>2026-11-01T08:00:00+01:00</_0:overallStartTime></_0:validityTimeSpecification></_0:validity>
    <_0:impact><_0:impactOnTraffic>congested</_0:impactOnTraffic></_0:impact>
    <_0:groupOfLocations><_0:locationContainedInGroup xsi:type="_0:Point"><_0:tpegpointLocation><_0:point><_0:pointCoordinates>
      <_0:latitude>43.2456</_0:latitude><_0:longitude>-2.9</_0:longitude></_0:pointCoordinates></_0:point></_0:tpegpointLocation>
      <_0:referencePointLinear><_0:roadNumber>N-634</_0:roadNumber><_0:referencePointDistance>23000.0</_0:referencePointDistance></_0:referencePointLinear>
    </_0:locationContainedInGroup></_0:groupOfLocations>
    <_0:constructionWorkType>constructionWork</_0:constructionWorkType>
   </_0:situationRecord></_0:situation>
  <_0:situation id="GUID_2"><_0:headerInformation><_0:informationStatus>real</_0:informationStatus></_0:headerInformation>
   <_0:situationRecord xsi:type="_0:MaintenanceWorks" id="GUID_2-1">
    <_0:validity><_0:validityStatus>active</_0:validityStatus></_0:validity>
    <_0:impact><_0:impactOnTraffic>impossible</_0:impactOnTraffic></_0:impact>
    <_0:groupOfLocations><_0:locationContainedInGroup xsi:type="_0:Linear"><_0:alertCLinear/>
      <_0:tpeglinearLocation><_0:from><_0:pointCoordinates><_0:latitude>41.61</_0:latitude><_0:longitude>2.1</_0:longitude></_0:pointCoordinates></_0:from>
      <_0:to><_0:pointCoordinates><_0:latitude>41.65</_0:latitude><_0:longitude>2.15</_0:longitude></_0:pointCoordinates></_0:to></_0:tpeglinearLocation>
    </_0:locationContainedInGroup></_0:groupOfLocations>
    <_0:effectOnRoadLayout>carriagewayClosures</_0:effectOnRoadLayout><_0:roadMaintenanceType>roadworks</_0:roadMaintenanceType>
   </_0:situationRecord></_0:situation>
  <_0:situation id="GUID_3"><_0:headerInformation><_0:informationStatus>real</_0:informationStatus></_0:headerInformation>
   <_0:situationRecord xsi:type="_0:MaintenanceWorks" id="GUID_3-1"><_0:validity><_0:validityStatus>active</_0:validityStatus></_0:validity>
    <_0:groupOfLocations><_0:locationContainedInGroup xsi:type="_0:Linear"><_0:alertCLinear/></_0:locationContainedInGroup></_0:groupOfLocations>
   </_0:situationRecord></_0:situation>
 </_0:payloadPublication></_0:d2LogicalModel>"""


def by_id(incs):
    return {i["i"].split(":")[1]: i for i in incs}


class ParseTest(unittest.TestCase):
    def test_v37(self):
        incs, pub, skipped = bt.parse_feed(V37, "dgt", NOW)
        m = by_id(incs)
        self.assertEqual(set(m), {"S1", "S2", "S3"})  # S4 caducada, S5 sin coordenadas
        self.assertEqual(skipped, 1)
        self.assertEqual(pub.year, 2026)
        self.assertEqual(m["S1"]["c"], "closure")
        self.assertEqual(m["S1"]["s"], 3)
        self.assertEqual(m["S1"]["r"], "HU-883")
        self.assertEqual(m["S2"]["c"], "works")
        self.assertEqual(m["S2"]["p"], [36.75545, -3.13054])
        self.assertEqual(m["S2"]["q"], [36.86577, -2.27011])
        self.assertEqual(m["S2"]["k"], 802.5)
        self.assertEqual(m["S2"]["d"], "eastBound")
        self.assertEqual(m["S3"]["c"], "accident")
        self.assertEqual(m["S3"]["t"], "Accidente a la altura del hotel")

    def test_v1_datex(self):
        incs, pub, skipped = bt.parse_feed(V1, "dtgv", NOW)
        m = by_id(incs)
        self.assertEqual(set(m), {"GUID_1", "GUID_2"})
        self.assertEqual(skipped, 1)  # GUID_3 solo AlertC, sin coordenadas
        self.assertEqual(m["GUID_1"]["c"], "works")
        self.assertEqual(m["GUID_1"]["s"], 2)  # obra con tráfico congestionado
        self.assertEqual(m["GUID_1"]["r"], "N-634")
        self.assertEqual(m["GUID_1"]["k"], 23.0)
        self.assertEqual(m["GUID_2"]["c"], "closure")
        self.assertEqual(m["GUID_2"]["s"], 3)

    def test_future_planned_is_hidden(self):
        future = V37.replace(b"2026-11-09T20:00:00+01:00", b"2026-12-01T20:00:00+01:00")
        incs, _, _ = bt.parse_feed(future, "dgt", NOW)
        self.assertNotIn("S2", by_id(incs))

    def test_classify(self):
        self.assertEqual(bt.classify("AbnormalTraffic", {"abnormalTrafficType": ["stationaryTraffic"]})[0], "congestion")
        self.assertEqual(bt.classify("Accident", {})[0], "accident")
        self.assertEqual(bt.classify("VehicleObstruction", {})[0], "obstruction")
        self.assertEqual(bt.classify("SpeedManagement", {})[0], "restriction")
        self.assertEqual(bt.classify("PoorEnvironmentConditions", {})[0], "weather")
        self.assertEqual(bt.classify("RoadOrCarriagewayOrLaneManagement",
                                     {"roadOrCarriagewayOrLaneManagementType": ["laneClosures"]})[0], "restriction")


class BuildTest(unittest.TestCase):
    def run_build(self, fetcher):
        d = tempfile.mkdtemp()
        meta = bt.build(d, now=NOW, fetcher=fetcher, sources={"dgt": "u1", "dtgv": "u2"})
        return d, meta

    def test_tiles_and_meta(self):
        d, meta = self.run_build(lambda u: V37 if u == "u1" else V1)
        self.assertTrue(meta["sources"]["dgt"]["ok"] and meta["sources"]["dtgv"]["ok"])
        files = set(os.listdir(os.path.join(d, "tiles")))
        self.assertIn("41_-1.json", files)  # HU-883 (41.70, -0.03) -> lat 41, lon floor(-0.03) = -1
        # la obra lineal A-7 (36.75,-3.13)->(36.86,-2.27) toca las celdas lon -4, -3 (y -3 a -2)
        self.assertIn("36_-4.json", files)
        self.assertIn("36_-3.json", files)
        with open(os.path.join(d, "tiles", "41_-1.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["r"], "HU-883")

    def test_failed_source_marked_not_ok(self):
        def f(u):
            if u == "u2":
                raise OSError("sin red")
            return V37
        d, meta = self.run_build(f)
        self.assertTrue(meta["sources"]["dgt"]["ok"])
        self.assertFalse(meta["sources"]["dtgv"]["ok"])


if __name__ == "__main__":
    unittest.main()
