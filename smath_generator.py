"""
SMath Generator Module para ThermoLab Suite v4.2.
Genera archivos .sm nativos completos con cabecera exacta de versión 1.5.0.9678,
ensamblados MathRegion, TextRegion y CoolProp Wrapper, escape estricto de entidades XML
y formato CRLF con BOM UTF-8 para compatibilidad absoluta con SMath Studio.
Soporta:
  - Kelvin-Planck / Clausius
  - Rankine Simple y con Recalentamiento (Reheat)
  - Brayton de Turbina de Gas
  - Refrigeración / Bomba de Calor
  - Certamen P1 (Turbina Vapor + Compresor Aire en eje)
  - Certamen P2 (Cilindro-Émbolo Transitorio)
  - Certamen P3 (Tobera enfriada por agua)
"""

import uuid
import html
from typing import List, Dict, Any

def create_smath_worksheet(title: str, regions_xml: str) -> str:
    ws_id = str(uuid.uuid4())
    safe_title = html.escape(title)
    
    xml = f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<?application progid="SMath Solver" version="1.5.0.9678"?>
<worksheet xmlns="http://smath.info/schemas/worksheet/1.0">
  <settings ppi="120">
    <identity>
      <id>{ws_id}</id>
      <revision>1</revision>
    </identity>
    <calculation>
      <precision>4</precision>
      <exponentialThreshold>3</exponentialThreshold>
      <trailingZeros>true</trailingZeros>
      <significantDigitsMode>true</significantDigitsMode>
      <mixedNumbers>true</mixedNumbers>
      <roundingMode>0</roundingMode>
      <approximateEqualAccuracy>0</approximateEqualAccuracy>
      <fractions>decimal</fractions>
    </calculation>
    <pageModel active="false" viewMode="2" printGrid="false" printAreas="true" simpleEqualsOnly="false" printBackgroundImages="true" hideElementsHighlightings="true">
      <paper id="9" orientation="Portrait" width="827" height="1169" />
      <margins left="39" right="39" top="49" bottom="49" />
      <header alignment="Center" color="#a9a9a9">&amp;[DATE] &amp;[TIME] - {safe_title}</header>
      <footer alignment="Center" color="#a9a9a9">&amp;[PAGENUM] / &amp;[COUNT]</footer>
      <backgrounds />
    </pageModel>
    <dependencies>
      <assembly name="SMath Core" version="1.75.9678.0" guid="a37cba83-b69c-4c71-9992-55ff666763bd" />
      <assembly name="MathRegion" version="1.75.9678.0" guid="02f1ab51-215b-466e-a74d-5d8b1cf85e8d" />
      <assembly name="PictureRegion" version="1.75.9678.0" guid="06b5df04-393e-4be7-9107-305196fcb861" />
      <assembly name="TextRegion" version="1.75.9678.0" guid="485d28c5-349a-48b6-93be-12a35a1c1e39" />
      <assembly name="CoolProp Wrapper" version="6.4.8214.13502" guid="ca92ef03-c7da-4888-98ad-528482733e2f" />
    </dependencies>
  </settings>
  <regions type="content">
{regions_xml}
  </regions>
</worksheet>"""

    xml = xml.replace("\r\n", "\n").replace("\n", "\r\n")
    return xml


def text_region(text: str, top: int, left: int = 10, is_title: bool = False) -> str:
    safe_text = html.escape(text)
    font_size = "12" if is_title else "10"
    height = "30" if is_title else "22"
    width = str(len(text) * 8 + 30)
    return f"""    <region left="{left}" top="{top}" width="{width}" height="{height}" color="#000000" fontSize="{font_size}">
      <text lang="spa" fontFamily="Arial Narrow" fontSize="{font_size}">
        <content>
          <p>{safe_text}</p>
        </content>
      </text>
    </region>"""


def assign_val(var: str, val: float, unit: str, top: int, left: int = 10) -> str:
    return f"""    <region left="{left}" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">{var}</e>
          <e type="operand">{val}</e>
          <e type="operand" style="unit">{unit}</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>"""


def assign_num(var: str, val: float, top: int, left: int = 10) -> str:
    return f"""    <region left="{left}" top="{top}" width="130" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">{var}</e>
          <e type="operand">{val}</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>"""


def coolprop_eval(var: str, prop: str, p1: str, v1_var: str, p2: str, v2_var: str, fluid: str, top: int, left: int = 10) -> str:
    return f"""    <region left="{left}" top="{top}" width="360" height="28" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">{var}</e>
          <e type="operand" style="string">{prop}</e>
          <e type="operand" style="string">{p1}</e>
          <e type="operand">{v1_var}</e>
          <e type="operand" style="string">{p2}</e>
          <e type="operand">{v2_var}</e>
          <e type="operand" style="string">{fluid}</e>
          <e type="function" args="6">CoolProp_Props</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>"""


# --- KELVIN / CLAUSIUS ---
def generate_kelvin_sm(data: Dict[str, Any]) -> str:
    top = 10
    reg = [text_region("MÁQUINAS TÉRMICAS DE KELVIN-PLANCK Y CLAUSIUS (COOLPROP & SMATH)", top, is_title=True)]
    top += 35
    reg.append(assign_val("TH", data["TH_C"] + 273.15, "K", top))
    reg.append(assign_val("TL", data["TL_C"] + 273.15, "K", top, left=200))
    reg.append(assign_val("T0", data["T0_C"] + 273.15, "K", top, left=400))
    top += 30
    reg.append(assign_val("QH", data["QH_kW"], "kW", top))
    reg.append(assign_val("QL", data["QL_kW"], "kW", top, left=200))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Wneto</e>
          <e type="operand">QH</e>
          <e type="operand">QL</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 30
    if data["sys_type"] in ('he', 'coupled'):
        reg.append(f"""    <region left="10" top="{top}" width="200" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">etath</e>
          <e type="operand">Wneto</e>
          <e type="operand">QH</e>
          <e type="operator" args="2">/</e>
          <e type="operand">100</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="220" top="{top}" width="220" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">etaCarnot</e>
          <e type="operand">1</e>
          <e type="operand">TL</e>
          <e type="operand">TH</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">-</e>
          <e type="operand">100</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        top += 40
        reg.append(f"""    <region left="10" top="{top}" width="260" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Sgen</e>
          <e type="operand">QL</e>
          <e type="operand">TL</e>
          <e type="operator" args="2">/</e>
          <e type="operand">QH</e>
          <e type="operand">TH</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    else:
        ql_var = "QL" if data["sys_type"] == "ref" else "QH"
        reg.append(f"""    <region left="10" top="{top}" width="180" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">COP</e>
          <e type="operand">{ql_var}</e>
          <e type="operand">Wneto</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        top += 40
        reg.append(f"""    <region left="10" top="{top}" width="260" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Sgen</e>
          <e type="operand">QH</e>
          <e type="operand">TH</e>
          <e type="operator" args="2">/</e>
          <e type="operand">QL</e>
          <e type="operand">TL</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40
    reg.append(f"""    <region left="10" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Xdest</e>
          <e type="operand">T0</e>
          <e type="operand">Sgen</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    return create_smath_worksheet("Maquina_Kelvin_Clausius", "\n".join(reg))


# --- RANKINE (SIMPLE O RECALENTAMIENTO) ---
def generate_rankine_sm(data: Dict[str, Any], params: Dict[str, Any]) -> str:
    top = 10
    reg = [text_region("CICLO RANKINE DE VAPOR DE AGUA (COOLPROP & SMATH)", top, is_title=True)]
    top += 35

    reheat = params.get("reheat", False)
    reg.append(assign_val("Pcond", params["P_low_kPa"], "kPa", top))
    reg.append(assign_val("Pcald", params["P_high_kPa"], "kPa", top, left=200))
    reg.append(assign_val("T3", params["T3_C"] + 273.15, "K", top, left=400))
    top += 30

    if reheat and params.get("P_reheat_kPa"):
        reg.append(assign_val("Preheat", params["P_reheat_kPa"], "kPa", top))
        t_reh = params.get("T_reheat_C") or params["T3_C"]
        reg.append(assign_val("T5", t_reh + 273.15, "K", top, left=200))
        top += 30

    reg.append(assign_num("etaT", params["eta_T"] / 100.0, top))
    reg.append(assign_num("etaB", params["eta_P"] / 100.0, top, left=200))
    reg.append(assign_val("fma", params["mdot"], "kg/s", top, left=400))
    top += 35

    # Estado 1: h1, s1
    reg.append(coolprop_eval("h1", "H", "P", "Pcond", "Q", "0", "Water", top))
    reg.append(coolprop_eval("s1", "S", "P", "Pcond", "Q", "0", "Water", top, left=380))
    top += 30

    # Estado 2s y 2
    reg.append(coolprop_eval("h2s", "H", "P", "Pcald", "S", "s1", "Water", top))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="220" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wB</e>
          <e type="operand">h2s</e>
          <e type="operand">h1</e>
          <e type="operator" args="2">-</e>
          <e type="operand">etaB</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h2</e>
          <e type="operand">h1</e>
          <e type="operand">wB</e>
          <e type="operator" args="2">+</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    # Estado 3: h3, s3
    reg.append(coolprop_eval("h3", "H", "P", "Pcald", "T", "T3", "Water", top))
    reg.append(coolprop_eval("s3", "S", "P", "Pcald", "T", "T3", "Water", top, left=380))
    top += 30

    if not reheat:
        # Simple: Estado 4s y 4
        reg.append(coolprop_eval("h4s", "H", "P", "Pcond", "S", "s3", "Water", top))
        top += 30
        reg.append(f"""    <region left="10" top="{top}" width="220" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wT</e>
          <e type="operand">etaT</e>
          <e type="operand">h3</e>
          <e type="operand">h4s</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h4</e>
          <e type="operand">h3</e>
          <e type="operand">wT</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        top += 35
        reg.append(coolprop_eval("x4", "Q", "P", "Pcond", "H", "h4", "Water", top))
        top += 35
        reg.append(f"""    <region left="10" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">qin</e>
          <e type="operand">h3</e>
          <e type="operand">h2</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="200" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wneto</e>
          <e type="operand">wT</e>
          <e type="operand">wB</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    else:
        # Reheat: 4s, 4 (HPT) -> 5 (Recal) -> 6s, 6 (LPT)
        reg.append(coolprop_eval("h4s", "H", "P", "Preheat", "S", "s3", "Water", top))
        top += 30
        reg.append(f"""    <region left="10" top="{top}" width="220" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wT1</e>
          <e type="operand">etaT</e>
          <e type="operand">h3</e>
          <e type="operand">h4s</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h4</e>
          <e type="operand">h3</e>
          <e type="operand">wT1</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        top += 35
        reg.append(coolprop_eval("h5", "H", "P", "Preheat", "T", "T5", "Water", top))
        reg.append(coolprop_eval("s5", "S", "P", "Preheat", "T", "T5", "Water", top, left=380))
        top += 30
        reg.append(coolprop_eval("h6s", "H", "P", "Pcond", "S", "s5", "Water", top))
        top += 30
        reg.append(f"""    <region left="10" top="{top}" width="220" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wT2</e>
          <e type="operand">etaT</e>
          <e type="operand">h5</e>
          <e type="operand">h6s</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h6</e>
          <e type="operand">h5</e>
          <e type="operand">wT2</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        top += 35
        reg.append(coolprop_eval("x6", "Q", "P", "Pcond", "H", "h6", "Water", top))
        top += 35
        reg.append(f"""    <region left="10" top="{top}" width="250" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">qin</e>
          <e type="operand">h3</e>
          <e type="operand">h2</e>
          <e type="operator" args="2">-</e>
          <e type="operand">h5</e>
          <e type="operand">h4</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">+</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
        reg.append(f"""    <region left="270" top="{top}" width="240" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wneto</e>
          <e type="operand">wT1</e>
          <e type="operand">wT2</e>
          <e type="operator" args="2">+</e>
          <e type="operand">wB</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    top += 35
    reg.append(f"""    <region left="10" top="{top}" width="200" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">etath</e>
          <e type="operand">wneto</e>
          <e type="operand">qin</e>
          <e type="operator" args="2">/</e>
          <e type="operand">100</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="220" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Wneto</e>
          <e type="operand">fma</e>
          <e type="operand">wneto</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    title = "Ciclo_Rankine_Recalentamiento" if reheat else "Ciclo_Rankine_CoolProp"
    return create_smath_worksheet(title, "\n".join(reg))


# --- BRAYTON DE GAS ---
def generate_brayton_sm(data: Dict[str, Any], params: Dict[str, Any]) -> str:
    top = 10
    reg = [text_region("CICLO BRAYTON DE TURBINA DE GAS (COOLPROP & SMATH)", top, is_title=True)]
    top += 35

    reg.append(assign_val("P1", params["P1_kPa"], "kPa", top))
    reg.append(assign_num("rp", params["rp"], top, left=200))
    reg.append(f"""    <region left="350" top="{top}" width="150" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">P2</e>
          <e type="operand">P1</e>
          <e type="operand">rp</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 30

    reg.append(assign_val("T1", params["T1_C"] + 273.15, "K", top))
    reg.append(assign_val("T3", params["T3_C"] + 273.15, "K", top, left=200))
    top += 30

    reg.append(assign_num("etaC", params["eta_C"] / 100.0, top))
    reg.append(assign_num("etaT", params["eta_T"] / 100.0, top, left=200))
    reg.append(assign_val("fma", params["mdot"], "kg/s", top, left=400))
    top += 35

    # Estados CoolProp
    reg.append(coolprop_eval("h1", "H", "P", "P1", "T", "T1", "Air", top))
    reg.append(coolprop_eval("s1", "S", "P", "P1", "T", "T1", "Air", top, left=380))
    top += 30

    reg.append(coolprop_eval("h2s", "H", "P", "P2", "S", "s1", "Air", top))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="220" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wC</e>
          <e type="operand">h2s</e>
          <e type="operand">h1</e>
          <e type="operator" args="2">-</e>
          <e type="operand">etaC</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h2</e>
          <e type="operand">h1</e>
          <e type="operand">wC</e>
          <e type="operator" args="2">+</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    reg.append(coolprop_eval("h3", "H", "P", "P2", "T", "T3", "Air", top))
    reg.append(coolprop_eval("s3", "S", "P", "P2", "T", "T3", "Air", top, left=380))
    top += 30

    reg.append(coolprop_eval("h4s", "H", "P", "P1", "S", "s3", "Air", top))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="220" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wT</e>
          <e type="operand">etaT</e>
          <e type="operand">h3</e>
          <e type="operand">h4s</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h4</e>
          <e type="operand">h3</e>
          <e type="operand">wT</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 35

    reg.append(f"""    <region left="10" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">qin</e>
          <e type="operand">h3</e>
          <e type="operand">h2</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="200" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">wneto</e>
          <e type="operand">wT</e>
          <e type="operand">wC</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="200" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">etath</e>
          <e type="operand">wneto</e>
          <e type="operand">qin</e>
          <e type="operator" args="2">/</e>
          <e type="operand">100</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="220" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Wneto</e>
          <e type="operand">fma</e>
          <e type="operand">wneto</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    return create_smath_worksheet("Ciclo_Brayton_Gas_CoolProp", "\n".join(reg))


# --- REFRIGERACIÓN ---
def generate_refrig_sm(data: Dict[str, Any], params: Dict[str, Any]) -> str:
    top = 10
    reg = []
    fl = params["fluid"]
    reg.append(text_region(f"CICLO DE REFRIGERACIÓN POR COMPRESIÓN ({fl.upper()})", top, is_title=True))
    top += 35

    reg.append(assign_val("Pevap", params["P_evap_kPa"], "kPa", top))
    reg.append(assign_val("Pcond", params["P_cond_kPa"], "kPa", top, left=200))
    reg.append(assign_num("etaC", params["eta_C"] / 100.0, top, left=400))
    top += 30

    reg.append(assign_val("fma", params["mdot"], "kg/s", top))
    top += 35

    reg.append(coolprop_eval("h1", "H", "P", "Pevap", "Q", "1", fl, top))
    reg.append(coolprop_eval("s1", "S", "P", "Pevap", "Q", "1", fl, top, left=380))
    top += 30

    reg.append(coolprop_eval("h2s", "H", "P", "Pcond", "S", "s1", fl, top))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="220" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">win</e>
          <e type="operand">h2s</e>
          <e type="operand">h1</e>
          <e type="operator" args="2">-</e>
          <e type="operand">etaC</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="250" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h2</e>
          <e type="operand">h1</e>
          <e type="operand">win</e>
          <e type="operator" args="2">+</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    reg.append(coolprop_eval("h3", "H", "P", "Pcond", "Q", "0", fl, top))
    top += 30
    reg.append(f"""    <region left="10" top="{top}" width="140" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">h4</e>
          <e type="operand">h3</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 35

    reg.append(f"""    <region left="10" top="{top}" width="200" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">QL</e>
          <e type="operand">fma</e>
          <e type="operand">h1</e>
          <e type="operand">h4</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="220" top="{top}" width="180" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Win</e>
          <e type="operand">fma</e>
          <e type="operand">win</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 35

    reg.append(f"""    <region left="10" top="{top}" width="160" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">COPR</e>
          <e type="operand">QL</e>
          <e type="operand">Win</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    return create_smath_worksheet(f"Refrigeracion_{fl}", "\n".join(reg))


# --- TOBERA ENFRIADA POR AGUA (PRUEBA 3) ---
def generate_nozzle_sm(data: Dict[str, Any], params: Dict[str, Any]) -> str:
    top = 10
    reg = [text_region("TOBERA DE AIRE CON ENFRIAMIENTO POR AGUA (COOLPROP & SMATH)", top, is_title=True)]
    top += 35

    reg.append(assign_val("Caudal1", params["Caudal1_m3s"], "m^3/s", top))
    reg.append(assign_val("P1", params["P1_kPa"], "kPa", top, left=200))
    reg.append(assign_val("T1", params["T1_C"] + 273.15, "K", top, left=380))
    top += 30

    reg.append(assign_val("A1", params["A1_m2"], "m^2", top))
    reg.append(assign_val("P2", params["P2_kPa"], "kPa", top, left=200))
    reg.append(assign_val("T2", params["T2_C"] + 273.15, "K", top, left=380))
    top += 30

    reg.append(assign_val("A2", params["A2_m2"], "m^2", top))
    reg.append(assign_val("Twin", params["Tw_in_C"] + 273.15, "K", top, left=200))
    reg.append(assign_val("Twout", params["Tw_out_C"] + 273.15, "K", top, left=380))
    top += 35

    reg.append(coolprop_eval("rho1", "D", "P", "P1", "T", "T1", "Air", top))
    reg.append(coolprop_eval("h1", "H", "P", "P1", "T", "T1", "Air", top, left=380))
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="200" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">fma</e>
          <e type="operand">rho1</e>
          <e type="operand">Caudal1</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="220" top="{top}" width="180" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Vel1</e>
          <e type="operand">Caudal1</e>
          <e type="operand">A1</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    reg.append(coolprop_eval("rho2", "D", "P", "P2", "T", "T2", "Air", top))
    reg.append(coolprop_eval("h2", "H", "P", "P2", "T", "T2", "Air", top, left=380))
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="200" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Vel2</e>
          <e type="operand">fma</e>
          <e type="operand">rho2</e>
          <e type="operand">A2</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    reg.append(f"""    <region left="10" top="{top}" width="360" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Qcedido</e>
          <e type="operand">fma</e>
          <e type="operand">0.5</e>
          <e type="operand">Vel1</e>
          <e type="operand">2</e>
          <e type="operator" args="2">^</e>
          <e type="operator" args="2">*</e>
          <e type="operand">h1</e>
          <e type="operator" args="2">+</e>
          <e type="operand">0.5</e>
          <e type="operand">Vel2</e>
          <e type="operand">2</e>
          <e type="operator" args="2">^</e>
          <e type="operator" args="2">*</e>
          <e type="operand">h2</e>
          <e type="operator" args="2">+</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    # Agua
    reg.append(coolprop_eval("hew", "H", "P", "100 'kPa'", "T", "Twin", "Water", top))
    reg.append(coolprop_eval("hsw", "H", "P", "100 'kPa'", "T", "Twout", "Water", top, left=380))
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="240" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">fmw</e>
          <e type="operand">Qcedido</e>
          <e type="operand">hsw</e>
          <e type="operand">hew</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    return create_smath_worksheet("Tobera_Enfriada_Agua", "\n".join(reg))


# --- CILINDRO-ÉMBOLO TRANSITORIO (PRUEBA 2) ---
def generate_piston_sm(data: Dict[str, Any], params: Dict[str, Any]) -> str:
    top = 10
    reg = [text_region("CILINDRO-ÉMBOLO TRANSITORIO CON INYECCIÓN DE VAPOR (COOLPROP)", top, is_title=True)]
    top += 35

    reg.append(assign_val("m1", params["m1_kg"], "kg", top))
    reg.append(assign_val("V1", params["V1_m3"], "m^3", top, left=180))
    reg.append(assign_val("P1", params["P1_kPa"], "kPa", top, left=360))
    top += 30

    reg.append(assign_val("V2", params["V2_m3"], "m^3", top))
    reg.append(assign_val("T2", params["T2_C"] + 273.15, "K", top, left=180))
    top += 30

    reg.append(assign_val("Pin", params["P_in_kPa"], "kPa", top))
    reg.append(assign_val("Tin", params["T_in_C"] + 273.15, "K", top, left=180))
    top += 35

    reg.append(f"""    <region left="10" top="{top}" width="160" height="35" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">v1</e>
          <e type="operand">V1</e>
          <e type="operand">m1</e>
          <e type="operator" args="2">/</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 40

    reg.append(coolprop_eval("u1", "U", "P", "P1", "D", "1 / v1", "Water", top))
    reg.append(coolprop_eval("s1", "S", "P", "P1", "D", "1 / v1", "Water", top, left=380))
    top += 30

    reg.append(coolprop_eval("rho2", "D", "P", "P1", "T", "T2", "Water", top))
    reg.append(coolprop_eval("u2", "U", "P", "P1", "T", "T2", "Water", top, left=380))
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">m2</e>
          <e type="operand">V2</e>
          <e type="operand">rho2</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    reg.append(f"""    <region left="180" top="{top}" width="160" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">min</e>
          <e type="operand">m2</e>
          <e type="operand">m1</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 35

    reg.append(coolprop_eval("hin", "H", "P", "Pin", "T", "Tin", "Water", top))
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="200" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Wfront</e>
          <e type="operand">P1</e>
          <e type="operand">V2</e>
          <e type="operand">V1</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")
    top += 30

    reg.append(f"""    <region left="10" top="{top}" width="320" height="24" color="#000000" fontSize="10">
      <math decimalPlaces="4" exponentialThreshold="3">
        <input>
          <e type="operand">Qtotal</e>
          <e type="operand">m2</e>
          <e type="operand">u2</e>
          <e type="operator" args="2">*</e>
          <e type="operand">m1</e>
          <e type="operand">u1</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">-</e>
          <e type="operand">Wfront</e>
          <e type="operator" args="2">+</e>
          <e type="operand">min</e>
          <e type="operand">hin</e>
          <e type="operator" args="2">*</e>
          <e type="operator" args="2">-</e>
          <e type="operator" args="2">:</e>
        </input>
      </math>
    </region>""")

    return create_smath_worksheet("Cilindro_Embolo_Transitorio", "\n".join(reg))
