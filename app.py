"""
Servidor FastAPI para Isenthalpy Studio v6.0 (Infalible CoolProp)
Sirve la API REST de cálculo, la descarga de hojas nativas de SMath Studio (.sm) con BOM UTF-8 y CRLF,
y los archivos estáticos de la interfaz web.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional

from thermo_engine import ThermoEngine
import smath_generator

app = FastAPI(title="Isenthalpy Studio v6.0 - Backend CoolProp", version="6.0", description="Plataforma Industrial de Termodinámica y Verificador SMath")

current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")

# Modelos Pydantic
class KelvinRequest(BaseModel):
    sys_type: str
    TH_C: float
    TL_C: float
    T0_C: float = 20.0
    mode: str
    val1: float
    val2: float
    TL_ref_C: Optional[float] = -15.0

class RankineRequest(BaseModel):
    P_high_kPa: float
    T3_C: float
    P_low_kPa: float
    eta_T: float = 85.0
    eta_P: float = 90.0
    mdot: float = 1.0
    T0_C: float = 20.0
    reheat: bool = False
    P_reheat_kPa: Optional[float] = None
    T_reheat_C: Optional[float] = None
    eta_T2: Optional[float] = None

class BraytonRequest(BaseModel):
    P1_kPa: float
    T1_C: float
    rp: float
    T3_C: float
    eta_C: float = 80.0
    eta_T: float = 85.0
    mdot: float = 1.0
    model: str = "coolprop"

class RefrigRequest(BaseModel):
    fluid: str = "R134a"
    P_evap_kPa: float
    P_cond_kPa: float
    eta_C: float = 85.0
    mdot: float = 0.05
    TL_C: float = -5.0
    TH_C: float = 25.0

class StateRequest(BaseModel):
    fluid: str
    p1_name: str
    p1_val: float
    p2_name: str
    p2_val: float

class NozzleRequest(BaseModel):
    Caudal1_m3s: float = 0.5
    P1_kPa: float = 300.0
    T1_C: float = 200.0
    A1_m2: float = 0.01
    P2_kPa: float = 100.0
    T2_C: float = 100.0
    A2_m2: float = 0.005
    Tw_in_C: float = 15.0
    Tw_out_C: float = 35.0
    Pw_kPa: float = 100.0
    T0_C: float = 25.0

class PistonRequest(BaseModel):
    m1_kg: float = 0.05
    V1_m3: float = 0.02
    P1_kPa: float = 200.0
    V2_m3: float = 0.06
    T2_C: float = 250.0
    P_in_kPa: float = 600.0
    T_in_C: float = 300.0
    P0_kPa: float = 101.0
    T0_C: float = 20.0

class TableGenRequest(BaseModel):
    fluid: str = "Water"
    table_type: str = "sat_T"
    val_min: float
    val_max: float
    step: float
    param_fixed: Optional[float] = None


# Endpoints API REST de Cálculo
@app.post("/api/kelvin")
def calc_kelvin(req: KelvinRequest):
    res = ThermoEngine.solve_kelvin_clausius(
        req.sys_type, req.TH_C, req.TL_C, req.T0_C, req.mode, req.val1, req.val2, req.TL_ref_C
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    res["TH_C"] = req.TH_C
    res["TL_C"] = req.TL_C
    res["T0_C"] = req.T0_C
    return res

@app.post("/api/rankine")
def calc_rankine(req: RankineRequest):
    try:
        return ThermoEngine.solve_rankine(
            req.P_high_kPa, req.T3_C, req.P_low_kPa, req.eta_T, req.eta_P, req.mdot, req.T0_C,
            reheat=req.reheat, P_reheat_kPa=req.P_reheat_kPa, T_reheat_C=req.T_reheat_C, eta_T2=req.eta_T2
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/brayton")
def calc_brayton(req: BraytonRequest):
    try:
        return ThermoEngine.solve_brayton(
            req.P1_kPa, req.T1_C, req.rp, req.T3_C, req.eta_C, req.eta_T, req.mdot, req.model
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/refrig")
def calc_refrig(req: RefrigRequest):
    try:
        return ThermoEngine.solve_refrig(
            req.fluid, req.P_evap_kPa, req.P_cond_kPa, req.eta_C, req.mdot, req.TL_C, req.TH_C
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/certamen/nozzle")
def calc_nozzle(req: NozzleRequest):
    try:
        return ThermoEngine.solve_nozzle_water_cooled(
            req.Caudal1_m3s, req.P1_kPa, req.T1_C, req.A1_m2,
            req.P2_kPa, req.T2_C, req.A2_m2,
            req.Tw_in_C, req.Tw_out_C, req.Pw_kPa, req.T0_C
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/certamen/piston")
def calc_piston(req: PistonRequest):
    try:
        return ThermoEngine.solve_piston_steam_transient(
            req.m1_kg, req.V1_m3, req.P1_kPa,
            req.V2_m3, req.T2_C,
            req.P_in_kPa, req.T_in_C,
            req.P0_kPa, req.T0_C
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/state")
def calc_state(req: StateRequest):
    res = ThermoEngine.get_state(req.fluid, req.p1_name, req.p1_val, req.p2_name, req.p2_val)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.get("/api/dome")
def calc_dome(fluid: str = "Water"):
    res = ThermoEngine.get_saturation_dome(fluid)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


# Helper para responder con archivo SMath .sm binario con BOM UTF-8 y CRLF
def make_smath_response(xml_str: str, filename: str):
    # Incluir BOM UTF-8 (\xef\xbb\xbf) requerido por SMath Studio para evitar errores de fin de archivo
    bom = b'\xef\xbb\xbf'
    content = bom + xml_str.encode("utf-8")
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# Endpoints de Generación y Descarga Nativa de Hojas de SMath Studio (.sm)
@app.post("/api/smath/download/kelvin")
def download_smath_kelvin(req: KelvinRequest):
    res = ThermoEngine.solve_kelvin_clausius(
        req.sys_type, req.TH_C, req.TL_C, req.T0_C, req.mode, req.val1, req.val2, req.TL_ref_C
    )
    res["TH_C"] = req.TH_C
    res["TL_C"] = req.TL_C
    res["T0_C"] = req.T0_C
    sm_xml = smath_generator.generate_kelvin_sm(res)
    return make_smath_response(sm_xml, "Maquina_Kelvin_Clausius.sm")

@app.post("/api/smath/download/rankine")
def download_smath_rankine(req: RankineRequest):
    res = ThermoEngine.solve_rankine(
        req.P_high_kPa, req.T3_C, req.P_low_kPa, req.eta_T, req.eta_P, req.mdot, req.T0_C,
        reheat=req.reheat, P_reheat_kPa=req.P_reheat_kPa, T_reheat_C=req.T_reheat_C, eta_T2=req.eta_T2
    )
    sm_xml = smath_generator.generate_rankine_sm(res, req.dict())
    fname = "Ciclo_Rankine_Recalentamiento.sm" if req.reheat else "Ciclo_Rankine_CoolProp.sm"
    return make_smath_response(sm_xml, fname)

@app.post("/api/smath/download/brayton")
def download_smath_brayton(req: BraytonRequest):
    res = ThermoEngine.solve_brayton(
        req.P1_kPa, req.T1_C, req.rp, req.T3_C, req.eta_C, req.eta_T, req.mdot, req.model
    )
    sm_xml = smath_generator.generate_brayton_sm(res, req.dict())
    return make_smath_response(sm_xml, "Ciclo_Brayton_Gas.sm")

@app.post("/api/smath/download/refrig")
def download_smath_refrig(req: RefrigRequest):
    res = ThermoEngine.solve_refrig(
        req.fluid, req.P_evap_kPa, req.P_cond_kPa, req.eta_C, req.mdot, req.TL_C, req.TH_C
    )
    sm_xml = smath_generator.generate_refrig_sm(res, req.dict())
    return make_smath_response(sm_xml, f"Refrigeracion_{req.fluid}.sm")

@app.post("/api/smath/download/nozzle")
def download_smath_nozzle(req: NozzleRequest):
    res = ThermoEngine.solve_nozzle_water_cooled(
        req.Caudal1_m3s, req.P1_kPa, req.T1_C, req.A1_m2,
        req.P2_kPa, req.T2_C, req.A2_m2,
        req.Tw_in_C, req.Tw_out_C, req.Pw_kPa, req.T0_C
    )
    sm_xml = smath_generator.generate_nozzle_sm(res, req.dict())
    return make_smath_response(sm_xml, "Tobera_Enfriada_Agua.sm")

@app.post("/api/smath/download/piston")
def download_smath_piston(req: PistonRequest):
    res = ThermoEngine.solve_piston_steam_transient(
        req.m1_kg, req.V1_m3, req.P1_kPa,
        req.V2_m3, req.T2_C,
        req.P_in_kPa, req.T_in_C,
        req.P0_kPa, req.T0_C
    )
    sm_xml = smath_generator.generate_piston_sm(res, req.dict())
    return make_smath_response(sm_xml, "Cilindro_Embolo_Transitorio.sm")


@app.post("/api/tables/generate")
def api_generate_table(req: TableGenRequest):
    try:
        return ThermoEngine.generate_table(
            req.fluid, req.table_type, req.val_min, req.val_max, req.step, req.param_fixed
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/pdf/cengel")
def get_cengel_pdf():
    pdf_path = os.path.join(current_dir, "Libros", "Cengel Yunus, Boles Michael - TERMODINAMICA (Spanish Edition)-McGraw-Hill Interamericana de España S.L. (2015).pdf")
    if os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=Cengel_Termodinamica_8va_Ed.pdf"}
        )
    raise HTTPException(status_code=404, detail="Archivo PDF del libro Çengel no encontrado en el servidor.")


# Servir Frontend
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    ico_path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    svg_path = os.path.join(static_dir, "favicon.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path, media_type="image/svg+xml")
    return Response(status_code=204)

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Isenthalpy Studio v6.0 Backend Activo"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
