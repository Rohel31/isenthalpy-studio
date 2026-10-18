"""
ThermoEngine v4.2 - Motor Analítico Integral de Termodinámica basada en CoolProp.
Incluye:
  1. Máquinas de Kelvin-Planck y Clausius (2ª Ley, Carnot, Sgen, Xdest).
  2. Ciclos de Potencia:
     - Rankine Simple (Ideal e Irreversible).
     - Rankine con Recalentamiento (Reheat: Alta Presión -> Recalentador -> Baja Presión).
     - Brayton de Gas (CoolProp variable y Gas Estándar Frío).
     - Ciclos Otto y Diesel de Combustión Interna.
  3. Ciclos de Refrigeración y Bomba de Calor (R134a, R410A, Ammonia) con curvas T-s y P-h.
  4. Módulo de Ejercicios de Certamen y Volúmenes de Control / Transitorios:
     - Sistema Acoplado Turbina de Vapor + Compresor de Aire en Eje (Prueba 1).
     - Cilindro-Émbolo Transitorio con Inyección de Vapor / Expansión (Prueba 2).
     - Tobera / Difusor con Energía Cinética e Intercambiador de Enfriamiento por Agua (Prueba 3).
  5. Desglose detallado de Exergía y Rendimiento de Segunda Ley (η_II) por componente.
"""

import math
from typing import Dict, Any, List, Optional
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI


class ThermoEngine:
    @staticmethod
    def get_state(fluid: str, p1_name: str, p1_val: float, p2_name: str, p2_val: float) -> Dict[str, Any]:
        """Calcula el estado termodinámico exacto vía CoolProp."""
        fluid_map = {
            'water': 'Water', 'agua': 'Water', 'air': 'Air', 'aire': 'Air',
            'r134a': 'R134a', 'r410a': 'R410A', 'ammonia': 'Ammonia', 'nitrogen': 'Nitrogen'
        }
        f_norm = fluid_map.get(fluid.lower(), fluid)

        conv = {
            'P': lambda v: v * 1e3,       # kPa -> Pa
            'T': lambda v: v + 273.15,    # °C -> K
            'Q': lambda v: max(0.0, min(1.0, v)),
            'S': lambda v: v * 1e3,       # kJ/(kg·K) -> J/(kg·K)
            'H': lambda v: v * 1e3,       # kJ/kg -> J/kg
            'D': lambda v: v
        }

        val1_si = conv[p1_name](p1_val)
        val2_si = conv[p2_name](p2_val)

        try:
            P_Pa = PropsSI('P', p1_name, val1_si, p2_name, val2_si, f_norm)
            T_K = PropsSI('T', p1_name, val1_si, p2_name, val2_si, f_norm)
            h_Jkg = PropsSI('H', p1_name, val1_si, p2_name, val2_si, f_norm)
            s_JkgK = PropsSI('S', p1_name, val1_si, p2_name, val2_si, f_norm)
            d_kgm3 = PropsSI('D', p1_name, val1_si, p2_name, val2_si, f_norm)
            u_Jkg = PropsSI('U', p1_name, val1_si, p2_name, val2_si, f_norm)
            
            try:
                q = PropsSI('Q', p1_name, val1_si, p2_name, val2_si, f_norm)
            except Exception:
                q = -1.0

            try:
                phase_idx = PropsSI('Phase', p1_name, val1_si, p2_name, val2_si, f_norm)
                phase_str = CP.get_phase_index_string(int(phase_idx))
            except Exception:
                phase_str = 'Desconocida'

            fase_desc = phase_str
            if q >= 0 and q <= 1:
                if abs(q) < 1e-4:
                    fase_desc = "Líquido Saturado (x=0)"
                elif abs(q - 1.0) < 1e-4:
                    fase_desc = "Vapor Saturado (x=1)"
                else:
                    fase_desc = f"Mezcla Bifásica (x={q:.4f})"
            elif "liquid" in phase_str.lower():
                fase_desc = "Líquido Subenfriado / Comprimido"
            elif "gas" in phase_str.lower() or "twophase" not in phase_str.lower():
                fase_desc = "Vapor Sobrecalentado / Gas"

            return {
                "success": True,
                "fluid": f_norm,
                "P_kPa": round(P_Pa / 1e3, 4),
                "T_C": round(T_K - 273.15, 3),
                "T_K": round(T_K, 3),
                "h_kJkg": round(h_Jkg / 1e3, 3),
                "s_kJkgK": round(s_JkgK / 1e3, 4),
                "u_kJkg": round(u_Jkg / 1e3, 3),
                "v_m3kg": round(1.0 / d_kgm3, 6),
                "rho_kgm3": round(d_kgm3, 4),
                "quality": round(q, 4) if (q >= 0 and q <= 1) else None,
                "phase": fase_desc
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------------- 1. KELVIN / CLAUSIUS ----------------
    @staticmethod
    def solve_kelvin_clausius(
        sys_type: str, TH_C: float, TL_C: float, T0_C: float, mode: str, val1: float, val2: float, TL_ref_C: Optional[float] = -15.0
    ) -> Dict[str, Any]:
        TH = TH_C + 273.15
        TL = TL_C + 273.15
        T0 = T0_C + 273.15

        if TH <= TL:
            return {"success": False, "error": "T_H debe ser mayor que T_L."}
        if TH <= 0 or TL <= 0 or T0 <= 0:
            return {"success": False, "error": "Las temperaturas absolutas deben ser mayores a 0 K."}

        if mode == 'QH_QL':
            QH, QL = val1, val2
            W = QH - QL
        elif mode == 'QH_W':
            QH, W = val1, val2
            QL = QH - W
        else:
            QL, W = val1, val2
            QH = QL + W

        if sys_type in ('he', 'coupled'):
            metric_name, carnot_name, law_name = "η_th (Kelvin)", "η_Carnot", "Enunciado de Kelvin-Planck"
            perf_real = (W / QH) if QH > 0 else 0.0
            perf_carnot = 1.0 - (TL / TH)
            Sgen = (QL / TL) - (QH / TH)
        elif sys_type == 'ref':
            metric_name, carnot_name, law_name = "COP_R (Clausius)", "COP_R,Carnot", "Enunciado de Clausius (Refrigerador)"
            perf_real = (QL / W) if W > 0 else 0.0
            perf_carnot = TL / (TH - TL)
            Sgen = (QH / TH) - (QL / TL)
        else:
            metric_name, carnot_name, law_name = "COP_HP (Clausius)", "COP_HP,Carnot", "Enunciado de Clausius (Bomba de Calor)"
            perf_real = (QH / W) if W > 0 else 0.0
            perf_carnot = TH / (TH - TL)
            Sgen = (QH / TH) - (QL / TL)

        Xdest = T0 * Sgen
        tol = 1e-5
        if W <= 0 or QL <= 0 or QH <= 0:
            verdict_type, verdict_title, verdict_msg = "danger", "FLUJOS DE ENERGÍA NO FÍSICOS", "Requiere calor y trabajo neto positivos."
        elif Sgen < -tol or perf_real > (perf_carnot + tol):
            verdict_type, verdict_title, verdict_msg = "danger", f"VIOLACIÓN DE LA 2ª LEY ({law_name.upper()})", f"Desempeño excede el límite de Carnot con S_gen = {Sgen:.5f} kW/K < 0."
        elif abs(Sgen) <= tol:
            verdict_type, verdict_title, verdict_msg = "warn", "CICLO REVERSIBLE IDEAL (Carnot)", "Opera en la frontera reversible teórica máxima (S_gen ≈ 0 kW/K)."
        else:
            verdict_type, verdict_title, verdict_msg = "ok", f"CICLO REAL FACTIBLE ({law_name})", f"Cumple la 2ª Ley con S_gen = +{Sgen:.5f} kW/K y X_dest = {Xdest:.2f} kW."

        coupled_data = None
        if sys_type == 'coupled':
            TL_ref_K = (TL_ref_C if TL_ref_C is not None else -15.0) + 273.15
            cop_c = TL_ref_K / (TL - TL_ref_K) if TL > TL_ref_K else 0.0
            coupled_data = {"COP_R_coupled_max": round(cop_c, 3), "QL_ref_max_kW": round(W * cop_c, 2), "TL_ref_C": TL_ref_C}

        smath_code = (
            f"// === RESOLUCIÓN SMATH STUDIO: MÁQUINA DE KELVIN-PLANCK / CLAUSIUS ===\n"
            f"TH := ({TH_C} + 273.15) 'K\nTL := ({TL_C} + 273.15) 'K\nT0 := ({T0_C} + 273.15) 'K\n\n"
            f"QH := {QH:.2f} 'kW\nQL := {QL:.2f} 'kW\nWneto := QH - QL = {W:.2f} 'kW\n\n"
        )
        if sys_type in ('he', 'coupled'):
            smath_code += f"etath := (Wneto / QH) * 100 = {perf_real*100:.2f} '%'\netaCarnot := (1 - TL / TH) * 100 = {perf_carnot*100:.2f} '%'\nSgen := (QL / TL) - (QH / TH) = {Sgen:.5f} 'kW/K'\n"
        elif sys_type == 'ref':
            smath_code += f"COPR := QL / Wneto = {perf_real:.4f}\nCOPRCarnot := TL / (TH - TL) = {perf_carnot:.4f}\nSgen := (QH / TH) - (QL / TL) = {Sgen:.5f} 'kW/K'\n"
        else:
            smath_code += f"COPHP := QH / Wneto = {perf_real:.4f}\nCOPHPCarnot := TH / (TH - TL) = {perf_carnot:.4f}\nSgen := (QH / TH) - (QL / TL) = {Sgen:.5f} 'kW/K'\n"
        smath_code += f"Xdest := T0 * Sgen = {Xdest:.3f} 'kW'"

        return {
            "success": True, "sys_type": sys_type, "TH_C": TH_C, "TL_C": TL_C, "T0_C": T0_C,
            "QH_kW": round(QH, 3), "QL_kW": round(QL, 3), "W_kW": round(W, 3),
            "perf_real": round(perf_real, 4), "perf_carnot": round(perf_carnot, 4), "metric_name": metric_name, "carnot_name": carnot_name,
            "Sgen_kW_K": round(Sgen, 5), "Xdest_kW": round(Xdest, 3), "verdict_type": verdict_type, "verdict_title": verdict_title,
            "verdict_msg": verdict_msg, "coupled": coupled_data, "smath_code": smath_code
        }

    # ---------------- 2. RANKINE SIMPLE Y CON RECALENTAMIENTO ----------------
    @staticmethod
    def solve_rankine(
        P_high_kPa: float, T3_C: float, P_low_kPa: float, eta_T: float, eta_P: float, mdot: float, T0_C: float = 20.0,
        reheat: bool = False, P_reheat_kPa: Optional[float] = None, T_reheat_C: Optional[float] = None, eta_T2: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Resuelve Rankine Simple o Rankine con Recalentamiento (Reheat).
        En recalentamiento:
          1: Salida condensador (P_low)
          2: Salida bomba (P_high)
          3: Entrada turbina de alta presión HPT (P_high, T3)
          4: Salida HPT (P_reheat)
          5: Salida recalentador / Entrada LPT (P_reheat, T_reheat)
          6: Salida turbina de baja presión LPT (P_low)
        """
        eta_T1_dec = (eta_T / 100.0) if eta_T > 1.0 else eta_T
        eta_T2_dec = ((eta_T2 if eta_T2 is not None else eta_T) / 100.0)
        eta_T2_dec = eta_T2_dec / 100.0 if eta_T2_dec > 1.0 else eta_T2_dec
        eta_P_dec = (eta_P / 100.0) if eta_P > 1.0 else eta_P

        P1_Pa = P_low_kPa * 1e3
        h1 = PropsSI('H', 'P', P1_Pa, 'Q', 0, 'Water')
        s1 = PropsSI('S', 'P', P1_Pa, 'Q', 0, 'Water')
        T1_K = PropsSI('T', 'P', P1_Pa, 'Q', 0, 'Water')
        v1 = 1.0 / PropsSI('D', 'P', P1_Pa, 'Q', 0, 'Water')

        P2_Pa = P_high_kPa * 1e3
        h2s = PropsSI('H', 'P', P2_Pa, 'S', s1, 'Water')
        wp_s = (h2s - h1)
        wp_real = wp_s / eta_P_dec if eta_P_dec > 0 else wp_s
        h2 = h1 + wp_real
        s2 = PropsSI('S', 'P', P2_Pa, 'H', h2, 'Water')
        T2_K = PropsSI('T', 'P', P2_Pa, 'H', h2, 'Water')

        T3_K = T3_C + 273.15
        h3 = PropsSI('H', 'P', P2_Pa, 'T', T3_K, 'Water')
        s3 = PropsSI('S', 'P', P2_Pa, 'T', T3_K, 'Water')

        T0_K = T0_C + 273.15

        if not reheat or not P_reheat_kPa:
            # Rankine Simple
            h4s = PropsSI('H', 'P', P1_Pa, 'S', s3, 'Water')
            wt_real = eta_T1_dec * (h3 - h4s)
            h4 = h3 - wt_real
            s4 = PropsSI('S', 'P', P1_Pa, 'H', h4, 'Water')
            T4_K = PropsSI('T', 'P', P1_Pa, 'H', h4, 'Water')
            try:
                q4 = PropsSI('Q', 'P', P1_Pa, 'H', h4, 'Water')
            except Exception:
                q4 = -1.0

            qin_Jkg = h3 - h2
            wnet_Jkg = wt_real - wp_real
            eta_th = (wnet_Jkg / qin_Jkg) if qin_Jkg > 0 else 0.0
            eta_carnot = 1.0 - (T1_K / T3_K)

            # Exergía por componente
            Sgen_t = mdot * (s4 - s3) / 1e3
            Xdest_t = T0_K * Sgen_t
            Sgen_p = mdot * (s2 - s1) / 1e3
            Xdest_p = T0_K * Sgen_p
            # Caldera: fuente a TH = T3_K
            Sgen_cald = mdot * ((s3 - s2) - (h3 - h2)/T3_K) / 1e3
            Xdest_cald = T0_K * Sgen_cald
            # Condensador: sumidero a TL = T1_K
            Sgen_cond = mdot * ((s1 - s4) + (h4 - h1)/T1_K) / 1e3
            Xdest_cond = T0_K * Sgen_cond

            exergy_breakdown = [
                {"component": "Caldera", "Xdest_kW": round(max(0, Xdest_cald), 2), "pct": 0},
                {"component": "Turbina", "Xdest_kW": round(Xdest_t, 2), "pct": 0},
                {"component": "Condensador", "Xdest_kW": round(max(0, Xdest_cond), 2), "pct": 0},
                {"component": "Bomba", "Xdest_kW": round(Xdest_p, 2), "pct": 0}
            ]
            X_total = sum(c["Xdest_kW"] for c in exergy_breakdown)
            if X_total > 0:
                for c in exergy_breakdown: c["pct"] = round(100 * c["Xdest_kW"] / X_total, 1)

            states = [
                {"id": "1", "desc": "Salida Condensador", "P_kPa": P_low_kPa, "T_C": T1_K - 273.15, "h_kJkg": h1/1e3, "s_kJkgK": s1/1e3, "phase": "Líq. Saturado (x=0)"},
                {"id": "2s", "desc": "Salida Bomba Ideal", "P_kPa": P_high_kPa, "T_C": PropsSI('T','P',P2_Pa,'S',s1,'Water')-273.15, "h_kJkg": h2s/1e3, "s_kJkgK": s1/1e3, "phase": "Líq. Comprimido"},
                {"id": "2", "desc": "Salida Bomba Real", "P_kPa": P_high_kPa, "T_C": T2_K - 273.15, "h_kJkg": h2/1e3, "s_kJkgK": s2/1e3, "phase": "Líq. Comprimido"},
                {"id": "3", "desc": "Entrada Turbina", "P_kPa": P_high_kPa, "T_C": T3_C, "h_kJkg": h3/1e3, "s_kJkgK": s3/1e3, "phase": "Vapor Sobrecalentado"},
                {"id": "4s", "desc": "Salida Turbina Ideal", "P_kPa": P_low_kPa, "T_C": PropsSI('T','P',P1_Pa,'S',s3,'Water')-273.15, "h_kJkg": h4s/1e3, "s_kJkgK": s3/1e3, "phase": f"Mezcla (x={PropsSI('Q','P',P1_Pa,'S',s3,'Water'):.4f})"},
                {"id": "4", "desc": "Salida Turbina Real", "P_kPa": P_low_kPa, "T_C": T4_K - 273.15, "h_kJkg": h4/1e3, "s_kJkgK": s4/1e3, "phase": f"Mezcla (x={q4:.4f})" if (q4>=0 and q4<=1) else "Vapor Sobrecalentado"}
            ]

            smath_code = (
                f"// === CICLO RANKINE SIMPLE EN SMATH STUDIO (COOLPROP) ===\n"
                f"Pcond := {P_low_kPa} 'kPa\nPcald := {P_high_kPa} 'kPa\nT3 := ({T3_C} + 273.15) 'K\n"
                f"etaT := {eta_T1_dec:.4f}\netaB := {eta_P_dec:.4f}\nfma := {mdot:.3f} 'kg/s\n\n"
                f"h1 := CoolProp_Props(\"H\"; \"P\"; Pcond; \"Q\"; 0; \"Water\") = {h1:.2f} 'J/kg'\n"
                f"s1 := CoolProp_Props(\"S\"; \"P\"; Pcond; \"Q\"; 0; \"Water\") = {s1:.3f} 'J/(kg*K)'\n"
                f"h2s := CoolProp_Props(\"H\"; \"P\"; Pcald; \"S\"; s1; \"Water\")\n"
                f"wB := (h2s - h1) / etaB = {wp_real:.2f} 'J/kg'\nh2 := h1 + wB\n"
                f"h3 := CoolProp_Props(\"H\"; \"P\"; Pcald; \"T\"; T3; \"Water\") = {h3:.2f} 'J/kg'\n"
                f"s3 := CoolProp_Props(\"S\"; \"P\"; Pcald; \"T\"; T3; \"Water\") = {s3:.3f} 'J/(kg*K)'\n"
                f"h4s := CoolProp_Props(\"H\"; \"P\"; Pcond; \"S\"; s3; \"Water\")\n"
                f"wT := etaT * (h3 - h4s) = {wt_real:.2f} 'J/kg'\nh4 := h3 - wT\n"
                f"x4 := CoolProp_Props(\"Q\"; \"P\"; Pcond; \"H\"; h4; \"Water\") = {q4:.4f}\n\n"
                f"qin := (h3 - h2) / 1000 = {qin_Jkg/1e3:.2f} 'kJ/kg'\n"
                f"wneto := (wT - wB) / 1000 = {wnet_Jkg/1e3:.2f} 'kJ/kg'\n"
                f"Wneto := fma * wneto = {mdot*wnet_Jkg/1e3:.2f} 'kW'\n"
                f"etath := (wneto / qin) * 100 = {eta_th*100:.2f} '%'"
            )

            return {
                "success": True, "reheat": False, "eta_th": round(eta_th * 100, 2), "eta_carnot": round(eta_carnot * 100, 2),
                "W_net_kW": round(mdot * wnet_Jkg / 1e3, 2), "W_t_kW": round(mdot * wt_real / 1e3, 2), "W_p_kW": round(mdot * wp_real / 1e3, 2),
                "Q_in_kW": round(mdot * qin_Jkg / 1e3, 2), "Q_out_kW": round(mdot * (h4 - h1) / 1e3, 2),
                "wnet_kJkg": round(wnet_Jkg / 1e3, 2), "qin_kJkg": round(qin_Jkg / 1e3, 2),
                "x4": round(q4, 4) if (q4>=0 and q4<=1) else "Sobrecalentado",
                "Xdest_total_kW": round(X_total, 2), "exergy_breakdown": exergy_breakdown,
                "states": states, "smath_code": smath_code
            }
        else:
            # Rankine con Recalentamiento (Reheat)
            Pr_Pa = P_reheat_kPa * 1e3
            T_reh = T_reheat_C if T_reheat_C is not None else T3_C
            T5_K = T_reh + 273.15

            # 4s y 4 (Salida HPT a P_reheat)
            h4s = PropsSI('H', 'P', Pr_Pa, 'S', s3, 'Water')
            wt1 = eta_T1_dec * (h3 - h4s)
            h4 = h3 - wt1
            s4 = PropsSI('S', 'P', Pr_Pa, 'H', h4, 'Water')
            T4_K = PropsSI('T', 'P', Pr_Pa, 'H', h4, 'Water')

            # 5 (Entrada LPT tras recalentamiento a Pr_Pa, T5_K)
            h5 = PropsSI('H', 'P', Pr_Pa, 'T', T5_K, 'Water')
            s5 = PropsSI('S', 'P', Pr_Pa, 'T', T5_K, 'Water')

            # 6s y 6 (Salida LPT a P1_Pa)
            h6s = PropsSI('H', 'P', P1_Pa, 'S', s5, 'Water')
            wt2 = eta_T2_dec * (h5 - h6s)
            h6 = h5 - wt2
            s6 = PropsSI('S', 'P', P1_Pa, 'H', h6, 'Water')
            T6_K = PropsSI('T', 'P', P1_Pa, 'H', h6, 'Water')
            try: q6 = PropsSI('Q', 'P', P1_Pa, 'H', h6, 'Water')
            except Exception: q6 = -1.0

            wt_total = wt1 + wt2
            qin_cald = (h3 - h2)
            qin_reh = (h5 - h4)
            qin_total = qin_cald + qin_reh
            wnet_Jkg = wt_total - wp_real
            eta_th = wnet_Jkg / qin_total

            # Exergías
            Sgen_t1 = mdot * (s4 - s3) / 1e3
            Sgen_t2 = mdot * (s6 - s5) / 1e3
            Xdest_t = T0_K * (Sgen_t1 + Sgen_t2)
            Xdest_p = T0_K * (mdot * (s2 - s1) / 1e3)
            Xdest_cald = T0_K * (mdot * ((s3 - s2) - qin_cald/T3_K + (s5 - s4) - qin_reh/T5_K) / 1e3)
            Xdest_cond = T0_K * (mdot * ((s1 - s6) + (h6 - h1)/T1_K) / 1e3)

            exergy_breakdown = [
                {"component": "Caldera & Recalentador", "Xdest_kW": round(max(0, Xdest_cald), 2), "pct": 0},
                {"component": "Turbinas HPT + LPT", "Xdest_kW": round(Xdest_t, 2), "pct": 0},
                {"component": "Condensador", "Xdest_kW": round(max(0, Xdest_cond), 2), "pct": 0},
                {"component": "Bomba", "Xdest_kW": round(Xdest_p, 2), "pct": 0}
            ]
            X_total = sum(c["Xdest_kW"] for c in exergy_breakdown)
            if X_total > 0:
                for c in exergy_breakdown: c["pct"] = round(100 * c["Xdest_kW"] / X_total, 1)

            states = [
                {"id": "1", "desc": "Salida Condensador", "P_kPa": P_low_kPa, "T_C": T1_K - 273.15, "h_kJkg": h1/1e3, "s_kJkgK": s1/1e3, "phase": "Líq. Sat (x=0)"},
                {"id": "2", "desc": "Salida Bomba", "P_kPa": P_high_kPa, "T_C": T2_K - 273.15, "h_kJkg": h2/1e3, "s_kJkgK": s2/1e3, "phase": "Líq. Comprimido"},
                {"id": "3", "desc": "Entrada HPT", "P_kPa": P_high_kPa, "T_C": T3_C, "h_kJkg": h3/1e3, "s_kJkgK": s3/1e3, "phase": "Vapor Sobrecal."},
                {"id": "4", "desc": "Salida HPT", "P_kPa": P_reheat_kPa, "T_C": T4_K - 273.15, "h_kJkg": h4/1e3, "s_kJkgK": s4/1e3, "phase": "Vapor"},
                {"id": "5", "desc": "Salida Recalentador", "P_kPa": P_reheat_kPa, "T_C": T_reh, "h_kJkg": h5/1e3, "s_kJkgK": s5/1e3, "phase": "Vapor Sobrecal."},
                {"id": "6", "desc": "Salida LPT", "P_kPa": P_low_kPa, "T_C": T6_K - 273.15, "h_kJkg": h6/1e3, "s_kJkgK": s6/1e3, "phase": f"Mezcla (x={q6:.4f})" if (q6>=0 and q6<=1) else "Vapor"}
            ]

            smath_code = (
                f"// === CICLO RANKINE CON RECALENTAMIENTO (REHEAT) EN SMATH STUDIO ===\n"
                f"Pcond := {P_low_kPa} 'kPa\nPcald := {P_high_kPa} 'kPa\nPreheat := {P_reheat_kPa} 'kPa\n"
                f"T3 := ({T3_C} + 273.15) 'K\nT5 := ({T_reh} + 273.15) 'K\n"
                f"etaT1 := {eta_T1_dec:.4f}\netaT2 := {eta_T2_dec:.4f}\netaB := {eta_P_dec:.4f}\nfma := {mdot:.3f} 'kg/s\n\n"
                f"h1 := CoolProp_Props(\"H\"; \"P\"; Pcond; \"Q\"; 0; \"Water\")\ns1 := CoolProp_Props(\"S\"; \"P\"; Pcond; \"Q\"; 0; \"Water\")\n"
                f"h2s := CoolProp_Props(\"H\"; \"P\"; Pcald; \"S\"; s1; \"Water\")\nwB := (h2s - h1) / etaB\nh2 := h1 + wB\n"
                f"h3 := CoolProp_Props(\"H\"; \"P\"; Pcald; \"T\"; T3; \"Water\")\ns3 := CoolProp_Props(\"S\"; \"P\"; Pcald; \"T\"; T3; \"Water\")\n"
                f"h4s := CoolProp_Props(\"H\"; \"P\"; Preheat; \"S\"; s3; \"Water\")\nwT1 := etaT1 * (h3 - h4s)\nh4 := h3 - wT1\n"
                f"h5 := CoolProp_Props(\"H\"; \"P\"; Preheat; \"T\"; T5; \"Water\")\ns5 := CoolProp_Props(\"S\"; \"P\"; Preheat; \"T\"; T5; \"Water\")\n"
                f"h6s := CoolProp_Props(\"H\"; \"P\"; Pcond; \"S\"; s5; \"Water\")\nwT2 := etaT2 * (h5 - h6s)\nh6 := h5 - wT2\n"
                f"x6 := CoolProp_Props(\"Q\"; \"P\"; Pcond; \"H\"; h6; \"Water\") = {q6:.4f}\n\n"
                f"qin := ((h3 - h2) + (h5 - h4)) / 1000 = {qin_total/1e3:.2f} 'kJ/kg'\n"
                f"wneto := (wT1 + wT2 - wB) / 1000 = {wnet_Jkg/1e3:.2f} 'kJ/kg'\n"
                f"Wneto := fma * wneto = {mdot*wnet_Jkg/1e3:.2f} 'kW'\n"
                f"etath := (wneto / qin) * 100 = {eta_th*100:.2f} '%'"
            )

            return {
                "success": True, "reheat": True, "eta_th": round(eta_th * 100, 2), "eta_carnot": round((1.0 - T1_K/max(T3_K, T5_K))*100, 2),
                "W_net_kW": round(mdot * wnet_Jkg / 1e3, 2), "W_t_kW": round(mdot * wt_total / 1e3, 2), "W_p_kW": round(mdot * wp_real / 1e3, 2),
                "Q_in_kW": round(mdot * qin_total / 1e3, 2), "Q_out_kW": round(mdot * (h6 - h1) / 1e3, 2),
                "wnet_kJkg": round(wnet_Jkg / 1e3, 2), "qin_kJkg": round(qin_total / 1e3, 2),
                "x4": round(q6, 4) if (q6>=0 and q6<=1) else "Sobrecalentado",
                "Xdest_total_kW": round(X_total, 2), "exergy_breakdown": exergy_breakdown,
                "states": states, "smath_code": smath_code
            }

    # ---------------- 3. BRAYTON DE GAS ----------------
    @staticmethod
    def solve_brayton(
        P1_kPa: float, T1_C: float, rp: float, T3_C: float, eta_C: float, eta_T: float, mdot: float, model: str = "coolprop"
    ) -> Dict[str, Any]:
        eta_C_dec = eta_C / 100.0 if eta_C > 1.0 else eta_C
        eta_T_dec = eta_T / 100.0 if eta_T > 1.0 else eta_T

        P1_Pa = P1_kPa * 1e3
        P2_Pa = P1_Pa * rp
        T1_K = T1_C + 273.15
        T3_K = T3_C + 273.15

        if model == "ideal_cold":
            k, cp = 1.4, 1.005
            T2s_K = T1_K * (rp ** ((k - 1) / k))
            T2_K = T1_K + (T2s_K - T1_K) / eta_C_dec
            T4s_K = T3_K * ((1.0 / rp) ** ((k - 1) / k))
            T4_K = T3_K - eta_T_dec * (T3_K - T4s_K)

            wc = cp * (T2_K - T1_K)
            wt = cp * (T3_K - T4_K)
            qin = cp * (T3_K - T2_K)
            wnet = wt - wc
            eta_th = wnet / qin if qin > 0 else 0.0
            rbw = wc / wt if wt > 0 else 0.0

            states = [
                {"id": "1", "desc": "Entrada Compresor", "P_kPa": P1_kPa, "T_K": round(T1_K, 2), "T_C": round(T1_C, 2), "h_kJkg": round(cp * T1_K, 2)},
                {"id": "2s", "desc": "Salida Comp. Isentrópica", "P_kPa": P1_kPa * rp, "T_K": round(T2s_K, 2), "T_C": round(T2s_K - 273.15, 2), "h_kJkg": round(cp * T2s_K, 2)},
                {"id": "2", "desc": "Salida Compresor Real", "P_kPa": P1_kPa * rp, "T_K": round(T2_K, 2), "T_C": round(T2_K - 273.15, 2), "h_kJkg": round(cp * T2_K, 2)},
                {"id": "3", "desc": "Entrada Turbina", "P_kPa": P1_kPa * rp, "T_K": round(T3_K, 2), "T_C": round(T3_C, 2), "h_kJkg": round(cp * T3_K, 2)},
                {"id": "4s", "desc": "Salida Turb. Isentrópica", "P_kPa": P1_kPa, "T_K": round(T4s_K, 2), "T_C": round(T4s_K - 273.15, 2), "h_kJkg": round(cp * T4s_K, 2)},
                {"id": "4", "desc": "Salida Turbina Real", "P_kPa": P1_kPa, "T_K": round(T4_K, 2), "T_C": round(T4_K - 273.15, 2), "h_kJkg": round(cp * T4_K, 2)}
            ]
        else:
            f = 'Air'
            h1 = PropsSI('H', 'P', P1_Pa, 'T', T1_K, f)
            s1 = PropsSI('S', 'P', P1_Pa, 'T', T1_K, f)
            h2s = PropsSI('H', 'P', P2_Pa, 'S', s1, f)
            T2s_K = PropsSI('T', 'P', P2_Pa, 'S', s1, f)
            h2 = h1 + (h2s - h1) / eta_C_dec
            T2_K = PropsSI('T', 'P', P2_Pa, 'H', h2, f)
            s2 = PropsSI('S', 'P', P2_Pa, 'H', h2, f)

            h3 = PropsSI('H', 'P', P2_Pa, 'T', T3_K, f)
            s3 = PropsSI('S', 'P', P2_Pa, 'T', T3_K, f)
            h4s = PropsSI('H', 'P', P1_Pa, 'S', s3, f)
            T4s_K = PropsSI('T', 'P', P1_Pa, 'S', s3, f)
            h4 = h3 - eta_T_dec * (h3 - h4s)
            T4_K = PropsSI('T', 'P', P1_Pa, 'H', h4, f)
            s4 = PropsSI('S', 'P', P1_Pa, 'H', h4, f)

            wc = (h2 - h1) / 1e3
            wt = (h3 - h4) / 1e3
            qin = (h3 - h2) / 1e3
            wnet = wt - wc
            eta_th = wnet / qin if qin > 0 else 0.0
            rbw = wc / wt if wt > 0 else 0.0

            states = [
                {"id": "1", "desc": "Entrada Compresor", "P_kPa": P1_kPa, "T_K": round(T1_K, 2), "T_C": round(T1_C, 2), "h_kJkg": round(h1/1e3, 2), "s_kJkgK": round(s1/1e3, 4)},
                {"id": "2s", "desc": "Salida Comp. Isentrópica", "P_kPa": P1_kPa * rp, "T_K": round(T2s_K, 2), "T_C": round(T2s_K - 273.15, 2), "h_kJkg": round(h2s/1e3, 2), "s_kJkgK": round(s1/1e3, 4)},
                {"id": "2", "desc": "Salida Compresor Real", "P_kPa": P1_kPa * rp, "T_K": round(T2_K, 2), "T_C": round(T2_K - 273.15, 2), "h_kJkg": round(h2/1e3, 2), "s_kJkgK": round(s2/1e3, 4)},
                {"id": "3", "desc": "Entrada Turbina", "P_kPa": P1_kPa * rp, "T_K": round(T3_K, 2), "T_C": round(T3_C, 2), "h_kJkg": round(h3/1e3, 2), "s_kJkgK": round(s3/1e3, 4)},
                {"id": "4s", "desc": "Salida Turb. Isentrópica", "P_kPa": P1_kPa, "T_K": round(T4s_K, 2), "T_C": round(T4s_K - 273.15, 2), "h_kJkg": round(h4s/1e3, 2), "s_kJkgK": round(s3/1e3, 4)},
                {"id": "4", "desc": "Salida Turbina Real", "P_kPa": P1_kPa, "T_K": round(T4_K, 2), "T_C": round(T4_K - 273.15, 2), "h_kJkg": round(h4/1e3, 2), "s_kJkgK": round(s4/1e3, 4)}
            ]

        W_net_kW = mdot * wnet
        smath_code = (
            f"// === CICLO BRAYTON EN SMATH STUDIO (COOLPROP) ===\n"
            f"P1 := {P1_kPa} 'kPa\nP2 := {P1_kPa * rp} 'kPa\nT1 := {T1_K:.2f} 'K\nT3 := {T3_K:.2f} 'K\n"
            f"etaC := {eta_C_dec:.4f}\netaT := {eta_T_dec:.4f}\nfma := {mdot:.3f} 'kg/s\n\n"
            f"h1 := CoolProp_Props(\"H\"; \"P\"; P1; \"T\"; T1; \"Air\")\ns1 := CoolProp_Props(\"S\"; \"P\"; P1; \"T\"; T1; \"Air\")\n"
            f"h2s := CoolProp_Props(\"H\"; \"P\"; P2; \"S\"; s1; \"Air\")\nh2 := h1 + (h2s - h1) / etaC\n"
            f"h3 := CoolProp_Props(\"H\"; \"P\"; P2; \"T\"; T3; \"Air\")\ns3 := CoolProp_Props(\"S\"; \"P\"; P2; \"T\"; T3; \"Air\")\n"
            f"h4s := CoolProp_Props(\"H\"; \"P\"; P1; \"S\"; s3; \"Air\")\nh4 := h3 - etaT * (h3 - h4s)\n\n"
            f"wneto := ((h3 - h4) - (h2 - h1)) / 1000 = {wnet:.2f} 'kJ/kg'\n"
            f"qin := (h3 - h2) / 1000 = {qin:.2f} 'kJ/kg'\n"
            f"Wneto := fma * wneto = {W_net_kW:.2f} 'kW'\n"
            f"etath := (wneto / qin) * 100 = {eta_th*100:.2f} '%'"
        )

        return {
            "success": True, "eta_th": round(eta_th * 100, 2), "rbw": round(rbw * 100, 2),
            "W_net_kW": round(W_net_kW, 2), "W_t_kW": round(mdot * wt, 2), "W_c_kW": round(mdot * wc, 2),
            "wnet_kJkg": round(wnet, 2), "qin_kJkg": round(qin, 2), "states": states, "smath_code": smath_code
        }

    # ---------------- 4. REFRIGERACIÓN Y BOMBA DE CALOR ----------------
    @staticmethod
    def solve_refrig(
        fluid: str, P_evap_kPa: float, P_cond_kPa: float, eta_C: float, mdot: float, TL_C: float = -5.0, TH_C: float = 25.0
    ) -> Dict[str, Any]:
        eta_C_dec = eta_C / 100.0 if eta_C > 1.0 else eta_C
        f = fluid

        P_evap_Pa = P_evap_kPa * 1e3
        h1 = PropsSI('H', 'P', P_evap_Pa, 'Q', 1, f)
        s1 = PropsSI('S', 'P', P_evap_Pa, 'Q', 1, f)
        T1_K = PropsSI('T', 'P', P_evap_Pa, 'Q', 1, f)

        P_cond_Pa = P_cond_kPa * 1e3
        h2s = PropsSI('H', 'P', P_cond_Pa, 'S', s1, f)
        T2s_K = PropsSI('T', 'P', P_cond_Pa, 'S', s1, f)
        w_in_ideal = (h2s - h1)
        w_in_real = w_in_ideal / eta_C_dec if eta_C_dec > 0 else w_in_ideal
        h2 = h1 + w_in_real
        T2_K = PropsSI('T', 'P', P_cond_Pa, 'H', h2, f)
        s2 = PropsSI('S', 'P', P_cond_Pa, 'H', h2, f)

        h3 = PropsSI('H', 'P', P_cond_Pa, 'Q', 0, f)
        s3 = PropsSI('S', 'P', P_cond_Pa, 'Q', 0, f)
        T3_K = PropsSI('T', 'P', P_cond_Pa, 'Q', 0, f)

        h4 = h3
        T4_K = T1_K
        s4 = PropsSI('S', 'P', P_evap_Pa, 'H', h4, f)
        q4 = PropsSI('Q', 'P', P_evap_Pa, 'H', h4, f)

        qL_Jkg = h1 - h4
        qH_Jkg = h2 - h3
        COP_R = qL_Jkg / w_in_real if w_in_real > 0 else 0.0
        COP_HP = qH_Jkg / w_in_real if w_in_real > 0 else 0.0

        TL_K = TL_C + 273.15
        TH_K = TH_C + 273.15
        COP_R_carnot = TL_K / (TH_K - TL_K) if (TH_K > TL_K) else 0.0
        COP_HP_carnot = TH_K / (TH_K - TL_K) if (TH_K > TL_K) else 0.0

        QL_kW = mdot * (qL_Jkg / 1e3)
        QH_kW = mdot * (qH_Jkg / 1e3)
        Win_kW = mdot * (w_in_real / 1e3)

        Sgen_comp = mdot * (s2 - s1) / 1e3
        Xdest_comp = TH_K * Sgen_comp
        Sgen_valv = mdot * (s4 - s3) / 1e3
        Xdest_valv = TH_K * Sgen_valv

        states = [
            {"id": "1", "desc": "Salida Evaporador", "P_kPa": P_evap_kPa, "T_C": round(T1_K - 273.15, 2), "h_kJkg": round(h1/1e3, 2), "s_kJkgK": round(s1/1e3, 4), "phase": "Vapor Sat (x=1)"},
            {"id": "2s", "desc": "Salida Comp. Ideal", "P_kPa": P_cond_kPa, "T_C": round(T2s_K - 273.15, 2), "h_kJkg": round(h2s/1e3, 2), "s_kJkgK": round(s1/1e3, 4), "phase": "Vapor Sobrecal."},
            {"id": "2", "desc": "Salida Compresor Real", "P_kPa": P_cond_kPa, "T_C": round(T2_K - 273.15, 2), "h_kJkg": round(h2/1e3, 2), "s_kJkgK": round(s2/1e3, 4), "phase": "Vapor Sobrecal."},
            {"id": "3", "desc": "Salida Condensador", "P_kPa": P_cond_kPa, "T_C": round(T3_K - 273.15, 2), "h_kJkg": round(h3/1e3, 2), "s_kJkgK": round(s3/1e3, 4), "phase": "Líq. Sat (x=0)"},
            {"id": "4", "desc": "Salida Válvula", "P_kPa": P_evap_kPa, "T_C": round(T4_K - 273.15, 2), "h_kJkg": round(h4/1e3, 2), "s_kJkgK": round(s4/1e3, 4), "phase": f"Mezcla (x={q4:.4f})"}
        ]

        smath_code = (
            f"// === CICLO DE REFRIGERACIÓN EN SMATH STUDIO ({f}) ===\n"
            f"Pevap := {P_evap_kPa} 'kPa\nPcond := {P_cond_kPa} 'kPa\netaC := {eta_C_dec:.4f}\nfma := {mdot:.3f} 'kg/s\n\n"
            f"h1 := CoolProp_Props(\"H\"; \"P\"; Pevap; \"Q\"; 1; \"{f}\") = {h1:.2f} 'J/kg'\n"
            f"s1 := CoolProp_Props(\"S\"; \"P\"; Pevap; \"Q\"; 1; \"{f}\") = {s1:.3f} 'J/(kg*K)'\n"
            f"h2s := CoolProp_Props(\"H\"; \"P\"; Pcond; \"S\"; s1; \"{f}\")\n"
            f"win := (h2s - h1) / etaC = {w_in_real:.2f} 'J/kg'\nh2 := h1 + win\n"
            f"h3 := CoolProp_Props(\"H\"; \"P\"; Pcond; \"Q\"; 0; \"{f}\") = {h3:.2f} 'J/kg'\nh4 := h3\n\n"
            f"QL := fma * (h1 - h4) / 1000 = {QL_kW:.3f} 'kW'\nWin := fma * (h2 - h1) / 1000 = {Win_kW:.3f} 'kW'\n"
            f"QH := fma * (h2 - h3) / 1000 = {QH_kW:.3f} 'kW'\nCOPR := QL / Win = {COP_R:.4f}\nCOPHP := QH / Win = {COP_HP:.4f}"
        )

        return {
            "success": True, "COP_R": round(COP_R, 3), "COP_HP": round(COP_HP, 3), "COP_R_carnot": round(COP_R_carnot, 3),
            "COP_HP_carnot": round(COP_HP_carnot, 3), "QL_kW": round(QL_kW, 3), "QH_kW": round(QH_kW, 3), "Win_kW": round(Win_kW, 3),
            "qL_kJkg": round(qL_Jkg / 1e3, 2), "win_kJkg": round(w_in_real / 1e3, 2), "x4": round(q4, 4),
            "Xdest_comp_kW": round(Xdest_comp, 3), "Xdest_valv_kW": round(Xdest_valv, 3), "states": states, "smath_code": smath_code
        }

    # ---------------- 5. DOMOS TERMODINÁMICOS (T-s y P-h) ----------------
    @staticmethod
    def get_saturation_dome(fluid: str = "Water", n_points: int = 50) -> Dict[str, Any]:
        f = fluid
        try:
            T_triple = PropsSI('T_triple', f)
            T_crit = PropsSI('T_critical', f)
            P_crit = PropsSI('pcrit', f)
            T_max = T_crit - 0.5
            T_min = max(T_triple + 1.0, 273.15 + 1.0) if f == 'Water' else (T_triple + 5.0)

            Ts = [T_min + i * (T_max - T_min) / (n_points - 1) for i in range(n_points)]
            
            s_liq, s_vap, h_liq, h_vap, P_sat_kPa, T_C = [], [], [], [], [], []

            for T in Ts:
                sl = PropsSI('S', 'T', T, 'Q', 0, f) / 1e3
                sv = PropsSI('S', 'T', T, 'Q', 1, f) / 1e3
                hl = PropsSI('H', 'T', T, 'Q', 0, f) / 1e3
                hv = PropsSI('H', 'T', T, 'Q', 1, f) / 1e3
                p = PropsSI('P', 'T', T, 'Q', 0, f) / 1e3
                s_liq.append(round(sl, 4))
                s_vap.append(round(sv, 4))
                h_liq.append(round(hl, 3))
                h_vap.append(round(hv, 3))
                P_sat_kPa.append(round(p, 2))
                T_C.append(round(T - 273.15, 2))

            return {
                "success": True, "fluid": f, "T_C": T_C, "s_liq": s_liq, "s_vap": s_vap,
                "h_liq": h_liq, "h_vap": h_vap, "P_sat_kPa": P_sat_kPa,
                "T_crit_C": round(T_crit - 273.15, 2), "P_crit_kPa": round(P_crit / 1e3, 2),
                "s_crit": round(PropsSI('S', 'T', T_crit, 'Q', 0, f) / 1e3, 4),
                "h_crit": round(PropsSI('H', 'T', T_crit, 'Q', 0, f) / 1e3, 3)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------------- 6. MÓDULO CERTÁMENES: DISPOSITIVOS & TRANSITORIOS ----------------
    @staticmethod
    def solve_nozzle_water_cooled(
        Caudal1_m3s: float, P1_kPa: float, T1_C: float, A1_m2: float,
        P2_kPa: float, T2_C: float, A2_m2: float,
        Tw_in_C: float, Tw_out_C: float, Pw_kPa: float = 100.0, T0_C: float = 25.0
    ) -> Dict[str, Any]:
        """
        Ejercicio Tobera de Aire Enfriada por Agua (Problema 2 / Ejercicio 3).
        """
        f_air = 'Air'
        f_water = 'Water'
        T1_K = T1_C + 273.15
        T2_K = T2_C + 273.15
        T0_K = T0_C + 273.15

        rho1 = PropsSI('D', 'P', P1_kPa * 1e3, 'T', T1_K, f_air)
        fma = rho1 * Caudal1_m3s
        Vel1 = Caudal1_m3s / A1_m2
        h1 = PropsSI('H', 'P', P1_kPa * 1e3, 'T', T1_K, f_air)
        s1 = PropsSI('S', 'P', P1_kPa * 1e3, 'T', T1_K, f_air)

        rho2 = PropsSI('D', 'P', P2_kPa * 1e3, 'T', T2_K, f_air)
        Vel2 = fma / (rho2 * A2_m2)
        h2 = PropsSI('H', 'P', P2_kPa * 1e3, 'T', T2_K, f_air)
        s2 = PropsSI('S', 'P', P2_kPa * 1e3, 'T', T2_K, f_air)

        # Calor cedido por el aire a la tobera:
        # Q = fma * [ (0.5*V1^2 + h1) - (0.5*V2^2 + h2) ]
        Q_J = fma * ((0.5 * (Vel1**2) + h1) - (0.5 * (Vel2**2) + h2))
        Q_kW = Q_J / 1e3

        # Agua de enfriamiento
        Tw_in_K = Tw_in_C + 273.15
        Tw_out_K = Tw_out_C + 273.15
        h_ew = PropsSI('H', 'P', Pw_kPa * 1e3, 'T', Tw_in_K, f_water)
        s_ew = PropsSI('S', 'P', Pw_kPa * 1e3, 'T', Tw_in_K, f_water)
        h_sw = PropsSI('H', 'P', Pw_kPa * 1e3, 'T', Tw_out_K, f_water)
        s_sw = PropsSI('S', 'P', Pw_kPa * 1e3, 'T', Tw_out_K, f_water)

        fmw = Q_J / (h_sw - h_ew) # kg/s

        # Segunda Ley y Destrucción de Exergía
        dS_aire = fma * (s2 - s1) # W/K
        dS_agua = fmw * (s_sw - s_ew) # W/K
        dS_total = dS_aire + dS_agua # W/K
        Irreversibilidad_kW = T0_K * dS_total / 1e3

        return {
            "success": True,
            "Vel1_ms": round(Vel1, 3), "Vel2_ms": round(Vel2, 4),
            "fma_kgs": round(fma, 4), "Q_kW": round(Q_kW, 4),
            "fmw_kgs": round(fmw, 4), "dS_aire_WK": round(dS_aire, 3),
            "dS_agua_WK": round(dS_agua, 3), "dS_total_WK": round(dS_total, 4),
            "Irreversibilidad_kW": round(Irreversibilidad_kW, 3)
        }

    @staticmethod
    def solve_piston_steam_transient(
        m1_kg: float, V1_m3: float, P1_kPa: float,
        V2_m3: float, T2_C: float,
        P_in_kPa: float, T_in_C: float,
        P0_kPa: float = 101.0, T0_C: float = 20.0
    ) -> Dict[str, Any]:
        """
        Ejercicio Tipo Prueba 2: Llenado Transitorio Cilindro-Émbolo con Vapor.
        """
        f = 'Water'
        T0_K = T0_C + 273.15
        P1_Pa = P1_kPa * 1e3
        v1_esp = V1_m3 / m1_kg

        # Estado 1: mezclar o subenfriado según v1
        u1 = PropsSI('U', 'P', P1_Pa, 'D', 1.0/v1_esp, f)
        s1 = PropsSI('S', 'P', P1_Pa, 'D', 1.0/v1_esp, f)
        h1 = PropsSI('H', 'P', P1_Pa, 'D', 1.0/v1_esp, f)
        try: x1 = PropsSI('Q', 'P', P1_Pa, 'D', 1.0/v1_esp, f)
        except Exception: x1 = -1.0

        # Estado 2: P1_kPa, T2_C
        T2_K = T2_C + 273.15
        rho2 = PropsSI('D', 'P', P1_Pa, 'T', T2_K, f)
        m2 = V2_m3 * rho2
        u2 = PropsSI('U', 'P', P1_Pa, 'T', T2_K, f)
        s2 = PropsSI('S', 'P', P1_Pa, 'T', T2_K, f)
        h2 = PropsSI('H', 'P', P1_Pa, 'T', T2_K, f)

        # Línea de entrada
        T_in_K = T_in_C + 273.15
        P_in_Pa = P_in_kPa * 1e3
        h_in = PropsSI('H', 'P', P_in_Pa, 'T', T_in_K, f)
        s_in = PropsSI('S', 'P', P_in_Pa, 'T', T_in_K, f)

        # Balances
        m_in = m2 - m1_kg
        W_frontera_J = P1_Pa * (V2_m3 - V1_m3)
        W_util_J = (P1_Pa - P0_kPa*1e3) * (V2_m3 - V1_m3)
        Q_total_J = (m2 * u2 - m1_kg * u1) + W_frontera_J - (m_in * h_in)

        # Exergías de Estado Cerrado y Flujo
        # Phi = m * [ (u - u0) + P0*(v - v0) - T0*(s - s0) ]
        # Exergía destruida
        T_sat_P1 = PropsSI('T', 'P', P1_Pa, 'Q', 0, f)
        Tb_med = 0.5 * (T_sat_P1 + T2_K) # Hipótesis pauta
        Sgen_J_K = (m2 * s2 - m1_kg * s1) - (m_in * s_in) - (Q_total_J / Tb_med)
        Xdest_J = T0_K * Sgen_J_K

        return {
            "success": True,
            "m1_kg": round(m1_kg, 4), "m2_kg": round(m2, 4), "m_in_kg": round(m_in, 5),
            "x1": round(x1, 4) if (x1>=0 and x1<=1) else "Sobrecal.",
            "W_frontera_kJ": round(W_frontera_J / 1e3, 2),
            "W_util_kJ": round(W_util_J / 1e3, 2),
            "Q_total_kJ": round(Q_total_J / 1e3, 2),
            "Sgen_J_K": round(Sgen_J_K, 2),
            "Xdest_kJ": round(Xdest_J / 1e3, 2)
        }

    @staticmethod
    def generate_table(fluid: str, table_type: str, val_min: float, val_max: float, step: float, param_fixed: Optional[float] = None) -> Dict[str, Any]:
        """Genera tablas termodinámicas exactas vía CoolProp NIST."""
        fluid_map = {
            'water': 'Water', 'agua': 'Water', 'air': 'Air', 'aire': 'Air',
            'r134a': 'R134a', 'r410a': 'R410A', 'ammonia': 'Ammonia', 'nitrogen': 'Nitrogen',
            'propane': 'Propane', 'co2': 'CarbonDioxide', 'carbondioxide': 'CarbonDioxide'
        }
        f_norm = fluid_map.get(fluid.lower(), fluid)
        rows = []
        
        if step <= 0:
            step = 1.0

        if table_type == 'sat_T':
            t_curr = val_min
            count = 0
            while t_curr <= val_max + 1e-5 and count < 500:
                count += 1
                try:
                    T_K = t_curr + 273.15
                    P_Pa = PropsSI('P', 'T', T_K, 'Q', 0, f_norm)
                    P_kPa = P_Pa / 1e3
                    vf = 1.0 / PropsSI('D', 'T', T_K, 'Q', 0, f_norm)
                    vg = 1.0 / PropsSI('D', 'T', T_K, 'Q', 1, f_norm)
                    uf = PropsSI('U', 'T', T_K, 'Q', 0, f_norm) / 1e3
                    ug = PropsSI('U', 'T', T_K, 'Q', 1, f_norm) / 1e3
                    hf = PropsSI('H', 'T', T_K, 'Q', 0, f_norm) / 1e3
                    hg = PropsSI('H', 'T', T_K, 'Q', 1, f_norm) / 1e3
                    sf = PropsSI('S', 'T', T_K, 'Q', 0, f_norm) / 1e3
                    sg = PropsSI('S', 'T', T_K, 'Q', 1, f_norm) / 1e3
                    rows.append({
                        "T_C": round(t_curr, 2),
                        "P_kPa": round(P_kPa, 3) if P_kPa < 100 else round(P_kPa, 2),
                        "vf": f"{vf:.6f}" if vf < 0.01 else f"{vf:.5f}",
                        "vg": f"{vg:.5f}" if vg < 10 else f"{vg:.4f}",
                        "uf": round(uf, 2), "ufg": round(ug - uf, 2), "ug": round(ug, 2),
                        "hf": round(hf, 2), "hfg": round(hg - hf, 2), "hg": round(hg, 2),
                        "sf": round(sf, 4), "sfg": round(sg - sf, 4), "sg": round(sg, 4)
                    })
                except Exception:
                    pass
                t_curr += step

        elif table_type == 'sat_P':
            p_curr = val_min
            count = 0
            while p_curr <= val_max + 1e-5 and count < 500:
                count += 1
                try:
                    P_Pa = p_curr * 1e3
                    T_K = PropsSI('T', 'P', P_Pa, 'Q', 0, f_norm)
                    T_C = T_K - 273.15
                    vf = 1.0 / PropsSI('D', 'P', P_Pa, 'Q', 0, f_norm)
                    vg = 1.0 / PropsSI('D', 'P', P_Pa, 'Q', 1, f_norm)
                    uf = PropsSI('U', 'P', P_Pa, 'Q', 0, f_norm) / 1e3
                    ug = PropsSI('U', 'P', P_Pa, 'Q', 1, f_norm) / 1e3
                    hf = PropsSI('H', 'P', P_Pa, 'Q', 0, f_norm) / 1e3
                    hg = PropsSI('H', 'P', P_Pa, 'Q', 1, f_norm) / 1e3
                    sf = PropsSI('S', 'P', P_Pa, 'Q', 0, f_norm) / 1e3
                    sg = PropsSI('S', 'P', P_Pa, 'Q', 1, f_norm) / 1e3
                    rows.append({
                        "P_kPa": round(p_curr, 2),
                        "T_C": round(T_C, 2),
                        "vf": f"{vf:.6f}" if vf < 0.01 else f"{vf:.5f}",
                        "vg": f"{vg:.5f}" if vg < 10 else f"{vg:.4f}",
                        "uf": round(uf, 2), "ufg": round(ug - uf, 2), "ug": round(ug, 2),
                        "hf": round(hf, 2), "hfg": round(hg - hf, 2), "hg": round(hg, 2),
                        "sf": round(sf, 4), "sfg": round(sg - sf, 4), "sg": round(sg, 4)
                    })
                except Exception:
                    pass
                p_curr += step

        elif table_type == 'sh_P':
            P_kPa = param_fixed if param_fixed is not None else 100.0
            P_Pa = P_kPa * 1e3
            try:
                T_sat_C = PropsSI('T', 'P', P_Pa, 'Q', 0, f_norm) - 273.15
            except Exception:
                T_sat_C = 0.0

            t_curr = max(val_min, T_sat_C + 0.1)
            count = 0
            while t_curr <= val_max + 1e-5 and count < 500:
                count += 1
                try:
                    T_K = t_curr + 273.15
                    v = 1.0 / PropsSI('D', 'P', P_Pa, 'T', T_K, f_norm)
                    u = PropsSI('U', 'P', P_Pa, 'T', T_K, f_norm) / 1e3
                    h = PropsSI('H', 'P', P_Pa, 'T', T_K, f_norm) / 1e3
                    s = PropsSI('S', 'P', P_Pa, 'T', T_K, f_norm) / 1e3
                    rows.append({
                        "P_kPa": round(P_kPa, 2),
                        "T_sat_C": round(T_sat_C, 2),
                        "T_C": round(t_curr, 2),
                        "v": f"{v:.5f}" if v < 10 else f"{v:.4f}",
                        "u": round(u, 2),
                        "h": round(h, 2),
                        "s": round(s, 4)
                    })
                except Exception:
                    pass
                t_curr += step

        return {
            "success": True,
            "fluid": f_norm,
            "table_type": table_type,
            "count": len(rows),
            "rows": rows
        }
