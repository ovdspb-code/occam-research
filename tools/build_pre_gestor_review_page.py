#!/usr/bin/env python
"""Build the public static Pre-Gestor review console."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


LANGS = ("es", "ru", "en")

DOMAIN_LABELS = {
    "authority_interactions": {
        "es": "Procedimientos tributarios",
        "ru": "Процедуры с налоговыми органами",
        "en": "Authority procedures",
    },
    "case_doctrine_watchlist": {
        "es": "Doctrina y casos de riesgo",
        "ru": "Практика и спорные критерии",
        "en": "Doctrine watchlist",
    },
    "corporate_tax_sl": {
        "es": "Impuesto sobre Sociedades",
        "ru": "Налог на прибыль компаний",
        "en": "Corporate tax",
    },
    "direct_tax_irpf_autonomo": {
        "es": "IRPF de autónomos",
        "ru": "IRPF для autónomo",
        "en": "IRPF for autonomos",
    },
    "direct_tax_irpf_personal": {
        "es": "IRPF personal",
        "ru": "Личный IRPF",
        "en": "Personal IRPF",
    },
    "fiscal_calendar": {
        "es": "Modelos y obligaciones comunes",
        "ru": "Основные формы и обязанности",
        "en": "Core forms",
    },
    "foreign_assets_international_tax": {
        "es": "IRNR y activos exteriores",
        "ru": "IRNR и зарубежные активы",
        "en": "IRNR / foreign assets",
    },
    "inbound_immigration_tax": {
        "es": "Entrada en España e inmigración fiscal",
        "ru": "Переезд в Испанию и налоговый статус",
        "en": "Inbound / immigration",
    },
    "indirect_tax_iva_igic": {
        "es": "IVA / IGIC",
        "ru": "IVA / IGIC",
        "en": "IVA / IGIC",
    },
    "local_municipal_tax": {
        "es": "Impuestos municipales",
        "ru": "Муниципальные налоги",
        "en": "Local municipal",
    },
    "property_transfer_wealth_inheritance": {
        "es": "Inmuebles, patrimonio y sucesiones",
        "ru": "Недвижимость, имущество и наследство",
        "en": "Property / wealth",
    },
    "rights_benefits_relief": {
        "es": "Derechos, beneficios y aplazamientos",
        "ru": "Права, льготы и отсрочки",
        "en": "Rights / relief",
    },
    "social_security_reta_labor": {
        "es": "Seguridad Social",
        "ru": "Социальное страхование",
        "en": "Social security",
    },
    "territorial_jurisdiction": {
        "es": "Territorio fiscal",
        "ru": "Фискальная территория",
        "en": "Territory",
    },
}

DOMAIN_PURPOSES = {
    "authority_interactions": {
        "es": "evitar perder plazos, pagar por la vía equivocada o contestar a una notificación sin saber qué procedimiento está abierto.",
        "ru": "не потерять срок, не выбрать неверный способ оплаты или обжалования и не отвечать на уведомление без понимания процедуры.",
        "en": "to avoid missing deadlines, choosing the wrong payment or appeal route, or answering a notice without knowing the procedure.",
    },
    "case_doctrine_watchlist": {
        "es": "separar un caso rutinario de uno que requiere criterio humano por doctrina administrativa o jurisprudencia.",
        "ru": "отделить обычный случай от ситуации, где нужна ручная правовая оценка из-за практики или спорного критерия.",
        "en": "to separate routine cases from situations that need human legal judgment because doctrine or case law may change the answer.",
    },
    "corporate_tax_sl": {
        "es": "evitar que una sociedad reciba una obligación, plazo, tipo o cálculo preliminar incorrecto.",
        "ru": "чтобы компания не получила неверную обязанность, срок, ставку или предварительный расчёт.",
        "en": "to prevent a company from receiving the wrong obligation, deadline, rate, or preliminary calculation route.",
    },
    "direct_tax_irpf_autonomo": {
        "es": "no convertir gastos, retenciones o pagos fraccionados de autónomo en una respuesta fiscal automática sin hechos verificados.",
        "ru": "не превращать расходы, удержания или авансовые платежи autónomo в автоматический налоговый ответ без проверенных фактов.",
        "en": "to avoid turning autonomo expenses, withholdings, or payments into an automatic tax answer without verified facts.",
    },
    "direct_tax_irpf_personal": {
        "es": "evitar una clasificación errónea de residencia, renta o deducciones personales antes de preparar la respuesta.",
        "ru": "избежать неверной классификации резидентства, дохода или личных вычетов до подготовки ответа.",
        "en": "to avoid misclassifying residence, income, or personal deductions before preparing the answer.",
    },
    "fiscal_calendar": {
        "es": "decidir si existe una obligación declarativa y qué datos faltan antes de hablar de importes o presentación.",
        "ru": "понять, есть ли обязанность подавать форму и каких данных не хватает до разговора о суммах или подаче.",
        "en": "to decide whether a filing obligation exists and what facts are missing before discussing amounts or submission.",
    },
    "foreign_assets_international_tax": {
        "es": "separar residencia, activos en el extranjero y umbrales informativos antes de afirmar una obligación.",
        "ru": "разделить резидентство, зарубежные активы и информационные пороги до утверждения обязанности.",
        "en": "to separate residence, foreign assets, and reporting thresholds before stating an obligation.",
    },
    "inbound_immigration_tax": {
        "es": "no confundir visado, residencia fiscal, régimen especial y Seguridad Social en una sola promesa al cliente.",
        "ru": "не смешать визу, налоговое резидентство, специальный режим и соцстрахование в одно обещание клиенту.",
        "en": "to avoid mixing visa status, tax residence, special regimes, and social security into one promise to the client.",
    },
    "indirect_tax_iva_igic": {
        "es": "identificar territorio, operación, periodo y régimen indirecto antes de hablar de IVA, IGIC o modelo concreto.",
        "ru": "определить территорию, операцию, период и режим косвенного налога до ответа про IVA, IGIC или форму.",
        "en": "to identify territory, transaction, period, and indirect-tax regime before giving an IVA, IGIC, or form answer.",
    },
    "local_municipal_tax": {
        "es": "comprobar municipio, ordenanza y hecho imponible antes de aplicar una regla local.",
        "ru": "проверить муниципалитет, местный регламент и событие налога до применения локального правила.",
        "en": "to check municipality, ordinance, and taxable event before applying a local rule.",
    },
    "property_transfer_wealth_inheritance": {
        "es": "separar el tipo de operación, punto de conexión territorial y tributo aplicable antes de estimar consecuencias.",
        "ru": "разделить тип операции, территориальную привязку и применимый налог до оценки последствий.",
        "en": "to separate transaction type, territorial connection, and applicable tax before estimating consequences.",
    },
    "rights_benefits_relief": {
        "es": "confirmar si el contribuyente tiene una vía de derecho, beneficio, rectificación o aplazamiento y qué prueba falta.",
        "ru": "подтвердить, есть ли у налогоплательщика путь права, льготы, исправления или отсрочки и каких доказательств не хватает.",
        "en": "to confirm whether the taxpayer has a rights, benefit, correction, or deferral route and what proof is missing.",
    },
    "social_security_reta_labor": {
        "es": "separar alta, cobertura, base y beneficios de Seguridad Social de la situación migratoria o fiscal.",
        "ru": "отделить регистрацию, покрытие, базу и льготы соцстраха от миграционного или налогового статуса.",
        "en": "to separate registration, coverage, contribution base, and benefits from migration or tax status.",
    },
    "territorial_jurisdiction": {
        "es": "resolver qué administración y territorio mandan antes de aplicar una regla estatal común.",
        "ru": "понять, какая администрация и территория компетентны, до применения общего государственного правила.",
        "en": "to resolve which authority and territory govern before applying a common state rule.",
    },
}

FOCUS_QUEUE = {
    "corporate.model_202_payment_on_account": {
        "label": "Gestor queue",
        "es": "Confirmar coeficientes de Modelo 202: 18%, 5/7 y 19/20, y la ruta 40.2 vs 40.3.",
        "ru": "Подтвердить коэффициенты Modelo 202: 18%, 5/7 и 19/20, и маршрут 40.2 vs 40.3.",
        "en": "Confirm Modelo 202 coefficients: 18%, 5/7 and 19/20, and the 40.2 vs 40.3 route.",
    },
    "common.corporate.model_200_202_candidate": {
        "label": "Gestor queue",
        "es": "Confirmar si la regla común 200/202 separa correctamente cierre contable, calendario y obligación de pago fraccionado.",
        "ru": "Подтвердить, что общее правило 200/202 корректно разделяет закрытие, календарь и обязанность авансового платежа.",
        "en": "Confirm that the common 200/202 route separates accounting close, calendar visibility and payment-on-account obligation.",
    },
    "procedure.appeals_sanctions_prescription": {
        "label": "Gestor queue",
        "es": "Confirmar LGT art. 188: reducciones 65/30/40 y condiciones de recurso/pago.",
        "ru": "Подтвердить LGT art. 188: reductions 65/30/40 и условия жалобы/оплаты.",
        "en": "Confirm LGT art. 188 reductions 65/30/40 and appeal/payment conditions.",
    },
    "inbound.beckham.art93_candidate": {
        "label": "Gestor queue",
        "es": "Confirmar cuerpos estatutarios Art. 93 LIRPF / Art. 116 RIRPF y plazos Modelos 149/151.",
        "ru": "Подтвердить тела норм Art. 93 LIRPF / Art. 116 RIRPF и сроки Modelos 149/151.",
        "en": "Confirm statutory bodies Art. 93 LIRPF / Art. 116 RIRPF and Modelo 149/151 timing.",
    },
    "doctrine.art93.director.property.escalation": {
        "label": "Gestor queue",
        "es": "Confirmar límites Beckham para administradores, participación y vivienda urbana.",
        "ru": "Подтвердить Beckham-ограничения для администраторов, доли участия и городской недвижимости.",
        "en": "Confirm Beckham limits for directors, shareholding and urban-property facts.",
    },
}

MANUAL_BRIEFS = {
    "inbound.beckham.art93_candidate": {
        "es": {
            "short_title": "Régimen Beckham: filtro previo del Art. 93",
            "question": "Revise si la regla filtra correctamente cuándo puede considerarse el régimen especial para impatriados, conocido como régimen Beckham.",
            "why": "Si este filtro falla, se puede prometer al cliente un régimen que no puede optar, perder el plazo del Modelo 149 o ignorar una exclusión por actividad o establecimiento permanente.",
            "law": "Base a revisar: Art. 93 de la Ley del IRPF; Reglamento del IRPF sobre opción, renuncia y exclusión; procedimientos AEAT de Modelos 149 y 151.",
            "verify": [
                "Que los cinco periodos impositivos anteriores no incluyan residencia fiscal española.",
                "Que el motivo de desplazamiento a España encaje en una vía admitida por la norma.",
                "Que la fecha inicial usada para contar los seis meses del Modelo 149 sea correcta.",
                "Que no haya exclusión por establecimiento permanente, actividad no admitida u otro bloqueo de Art. 93.",
            ],
            "boundary": "No se decide aquí si un cliente concreto queda aceptado ni se prepara la presentación. Se revisa si la regla y sus fuentes sirven como filtro previo para gestor.",
            "expected": "Marque «Confirmar tal cual» solo si el filtro, el plazo, las exclusiones y las fuentes son correctos. Use «Confirmar tras corrección» si falta una condición, plazo, fuente o matiz público.",
        },
        "ru": {
            "short_title": "Режим Бекхэма: предварительный фильтр Art. 93",
            "question": "Проверьте, правильно ли правило отбирает случаи, где вообще можно рассматривать специальный режим для прибывающих в Испанию специалистов, известный как режим Бекхэма.",
            "why": "Если фильтр ошибается, клиенту могут пообещать режим, который он не вправе выбрать, пропустить срок Modelo 149 или не заметить исключение по деятельности или постоянному представительству.",
            "law": "Правовая опора для проверки: Art. 93 Ley del IRPF; Reglamento del IRPF о выборе, отказе и исключении из режима; процедуры AEAT по Modelos 149 и 151.",
            "verify": [
                "Пять предыдущих налоговых периодов без испанского налогового резидентства.",
                "Основание переезда в Испанию подходит под допустимый путь режима.",
                "Дата, от которой считается шестимесячный срок Modelo 149, выбрана правильно.",
                "Нет блокировки из-за постоянного представительства, неподходящей деятельности или другого исключения Art. 93.",
            ],
            "boundary": "Здесь не подтверждается окончательное право конкретного клиента и не готовится подача. Проверяется, годится ли правило и его источники как предварительный фильтр для гестора.",
            "expected": "Нажмите «Подтвердить как есть», только если фильтр, срок, исключения и источники верны. «Подтвердить после правки» — если не хватает условия, срока, источника или безопасной формулировки.",
        },
        "en": {
            "short_title": "Beckham regime: Art. 93 pre-filter",
            "question": "Check whether the rule correctly filters cases where Spain's special inbound-worker regime, commonly called the Beckham regime, may even be considered.",
            "why": "If this filter is wrong, a client may be promised an unavailable regime, miss the Modelo 149 deadline, or overlook an exclusion for activity type or permanent establishment.",
            "law": "Legal basis to check: Art. 93 of the IRPF Law; IRPF Regulation rules on opting in, waiver and exclusion; AEAT procedures for Modelos 149 and 151.",
            "verify": [
                "No Spanish tax residence in the five previous tax periods.",
                "The reason for moving to Spain fits an admitted route under the regime.",
                "The start date used for the six-month Modelo 149 window is correct.",
                "No exclusion applies because of permanent establishment, disallowed activity or another Art. 93 blocker.",
            ],
            "boundary": "This does not approve a specific client's regime or prepare a filing. It checks whether the rule and sources work as a pre-filter for a gestor.",
            "expected": "Choose “Confirm as-is” only if the filter, deadline, exclusions and sources are correct. Choose “Confirm after fix” when a condition, deadline, source or public wording must change.",
        },
    },
    "corporate.model_202_payment_on_account": {
        "es": {
            "short_title": "Modelo 202: pago fraccionado de sociedades",
            "question": "Revise si la regla decide correctamente cuándo una sociedad debe revisar el Modelo 202 y qué modalidad de pago fraccionado corresponde.",
            "why": "Un error puede llevar a pedir un pago fraccionado indebido, omitir uno obligatorio o calcularlo con una modalidad equivocada.",
            "law": "Base a revisar: Ley del Impuesto sobre Sociedades; página AEAT de Modelo 202; criterios AEAT sobre modalidades de pago fraccionado y calendario aplicable.",
            "verify": [
                "Si la sociedad entra por la modalidad del art. 40.2 o por la modalidad del art. 40.3.",
                "Si existen datos del Modelo 200 anterior o contabilidad intermedia suficiente.",
                "Si los coeficientes 18%, 5/7 y 19/20 se usan solo en el supuesto que corresponde.",
                "Si periodo, territorio y estado censal permiten hablar del Modelo 202.",
            ],
            "boundary": "No se calcula el importe final ni se presenta el modelo. Se revisa la ruta lógica y las fuentes.",
            "expected": "Marque «Confirmar tal cual» si la ruta 40.2/40.3, los coeficientes y las fuentes están bien. Marque «Confirmar tras corrección» si hay que cambiar cálculo, umbral, periodo o explicación.",
        },
        "ru": {
            "short_title": "Modelo 202: авансовый платёж по налогу на прибыль компании",
            "question": "Проверьте, правильно ли правило определяет, когда компании нужно рассматривать Modelo 202 и какой способ авансового платежа применять.",
            "why": "Ошибка приведёт к лишнему авансовому платежу, пропуску обязательного платежа или расчёту по неверной методике.",
            "law": "Правовая опора для проверки: Ley del Impuesto sobre Sociedades; страница AEAT по Modelo 202; правила AEAT о modalidades de pago fraccionado и применимом календаре.",
            "verify": [
                "Компания идёт по методу art. 40.2 или по методу art. 40.3.",
                "Есть ли данные предыдущего Modelo 200 или промежуточная бухгалтерия для расчёта.",
                "Коэффициенты 18%, 5/7 и 19/20 используются только в подходящем сценарии.",
                "Период, территория и census-статус позволяют говорить именно о Modelo 202.",
            ],
            "boundary": "Здесь не считается финальная сумма и не подаётся форма. Проверяется логический маршрут и источники.",
            "expected": "Нажмите «Подтвердить как есть», если маршрут 40.2/40.3, коэффициенты и источники верны. «Подтвердить после правки» — если нужно менять расчёт, порог, период или объяснение.",
        },
        "en": {
            "short_title": "Modelo 202: corporate payment on account",
            "question": "Check whether the rule correctly decides when a company must consider Modelo 202 and which payment-on-account modality applies.",
            "why": "An error may create an unnecessary payment, miss a required one, or calculate it through the wrong method.",
            "law": "Legal basis to check: Corporate Income Tax Law; AEAT Modelo 202 page; AEAT payment-on-account modalities and applicable calendar.",
            "verify": [
                "Whether the company falls under the art. 40.2 route or the art. 40.3 route.",
                "Whether prior Modelo 200 data or interim accounts are available for the calculation.",
                "Whether 18%, 5/7 and 19/20 coefficients are used only in the correct scenario.",
                "Whether period, territory and census status support a Modelo 202 discussion.",
            ],
            "boundary": "This does not calculate the final amount or file the form. It checks the logic route and source support.",
            "expected": "Choose “Confirm as-is” if the 40.2/40.3 route, coefficients and sources are correct. Choose “Confirm after fix” if calculation, threshold, period or explanation must change.",
        },
    },
    "common.corporate.model_200_202_candidate": {
        "es": {
            "short_title": "Sociedades: separar Modelo 200, Modelo 202 y cierre",
            "question": "Revise si la regla separa correctamente la declaración anual de Sociedades, los pagos fraccionados y el cierre contable.",
            "why": "Una regla común demasiado amplia puede mezclar calendario, obligación de pago y cierre contable, generando respuestas imprecisas.",
            "law": "Base a revisar: Ley del Impuesto sobre Sociedades; procedimientos AEAT de Modelos 200 y 202; calendario AEAT aplicable.",
            "verify": [
                "Que Modelo 200 y Modelo 202 no se traten como la misma obligación.",
                "Que el cierre contable sea requisito de preparación, no una presentación automática.",
                "Que periodo, territorio y sujeto pasivo queden verificados antes de hablar de importes.",
            ],
            "boundary": "No se calcula cuota ni pago fraccionado. Se valida que la regla enrute el caso al bloque correcto.",
            "expected": "Marque «Confirmar tal cual» si la separación 200/202/cierre está clara; si no, indique qué bloque se mezcla.",
        },
        "ru": {
            "short_title": "Sociedades: разделить Modelo 200, Modelo 202 и закрытие",
            "question": "Проверьте, правильно ли правило разделяет годовую декларацию по налогу на прибыль компании, авансовые платежи и бухгалтерское закрытие.",
            "why": "Слишком общее правило может смешать календарь, обязанность авансового платежа и закрытие учёта, а пользователь получит неточный ответ.",
            "law": "Правовая опора для проверки: Ley del Impuesto sobre Sociedades; процедуры AEAT по Modelos 200 и 202; применимый календарь AEAT.",
            "verify": [
                "Modelo 200 и Modelo 202 не представлены как одна и та же обязанность.",
                "Бухгалтерское закрытие — этап подготовки, а не автоматическая подача.",
                "Период, территория и налогоплательщик проверяются до разговора о суммах.",
            ],
            "boundary": "Здесь не рассчитывается налог или авансовый платёж. Проверяется, ведёт ли правило в правильный блок.",
            "expected": "Нажмите «Подтвердить как есть», если разделение 200/202/закрытия понятно; иначе укажите, какие блоки смешаны.",
        },
        "en": {
            "short_title": "Corporate tax: separate Modelo 200, Modelo 202 and closing",
            "question": "Check whether the rule separates the annual corporate return, payments on account and accounting close.",
            "why": "An over-broad common rule can mix calendar, payment obligation and accounting close, producing imprecise answers.",
            "law": "Legal basis to check: Corporate Income Tax Law; AEAT procedures for Modelos 200 and 202; applicable AEAT calendar.",
            "verify": [
                "Modelo 200 and Modelo 202 are not treated as the same obligation.",
                "Accounting close is a preparation requirement, not an automatic filing.",
                "Period, territory and taxpayer status are verified before amounts are discussed.",
            ],
            "boundary": "This does not calculate tax due or a payment on account. It validates whether the rule routes the case to the correct block.",
            "expected": "Choose “Confirm as-is” if the 200/202/closing separation is clear; otherwise state which blocks are mixed.",
        },
    },
    "territorial.foral.threshold.allocation": {
        "es": {
            "short_title": "Navarra y País Vasco: umbral de reparto IVA",
            "question": "Revise si la regla resuelve correctamente cuándo una operación debe salir del circuito estatal común hacia Navarra o País Vasco.",
            "why": "Si la competencia territorial se decide mal, todo lo posterior —modelo, administración, plazo y cálculo— puede quedar mal encaminado.",
            "law": "Base a revisar: Convenio Económico de Navarra y Concierto Económico del País Vasco, especialmente los artículos de reparto IVA en el BOE consolidado.",
            "verify": [
                "Que el umbral de volumen de operaciones usado para IVA sea el correcto y no se copie de otra materia sin comprobar el artículo.",
                "Que se distingan Navarra, País Vasco y territorio común.",
                "Que la regla bloquee los modelos estatales cuando primero hace falta resolver competencia foral.",
            ],
            "boundary": "No se liquida IVA ni Impuesto sobre Sociedades. Se revisa la puerta territorial previa.",
            "expected": "Marque «Confirmar tal cual» si el umbral, territorio y fuente BOE son correctos. Marque «Confirmar tras corrección» si el número o artículo no coincide.",
        },
        "ru": {
            "short_title": "Navarra и País Vasco: порог распределения IVA",
            "question": "Проверьте, правильно ли правило определяет, когда случай должен уходить из общего государственного контура в Navarra или País Vasco.",
            "why": "Если территориальная компетенция выбрана неверно, дальше ошибочными станут форма, администрация, срок и расчёт.",
            "law": "Правовая опора для проверки: Convenio Económico de Navarra и Concierto Económico del País Vasco, особенно статьи о распределении IVA в консолидированном BOE.",
            "verify": [
                "Порог объёма операций для IVA взят из правильной статьи, а не перенесён из другой налоговой темы без проверки.",
                "Navarra, País Vasco и territorio común разведены отдельно.",
                "Правило блокирует государственные формы, если сначала нужно решить foral-компетенцию.",
            ],
            "boundary": "Здесь не рассчитывается IVA или налог на прибыль. Проверяется предварительный территориальный шлюз.",
            "expected": "Нажмите «Подтвердить как есть», если порог, территория и BOE-источник верны. «Подтвердить после правки» — если число или статья не совпадает.",
        },
        "en": {
            "short_title": "Navarra and Basque Country: IVA allocation threshold",
            "question": "Check whether the rule correctly decides when a case must leave the common state route for Navarra or the Basque Country.",
            "why": "If territorial competence is wrong, every later step — form, authority, deadline and calculation — may be routed incorrectly.",
            "law": "Legal basis to check: Navarra Economic Agreement and Basque Country Economic Accord, especially the BOE consolidated IVA allocation articles.",
            "verify": [
                "The IVA turnover threshold comes from the correct article and is not copied from another tax without checking.",
                "Navarra, Basque Country and common territory are kept separate.",
                "The rule blocks state forms when foral competence must be resolved first.",
            ],
            "boundary": "This does not liquidate IVA or corporate income tax. It checks the prior territorial gate.",
            "expected": "Choose “Confirm as-is” if threshold, territory and BOE source are correct. Choose “Confirm after fix” if the number or article does not match.",
        },
    },
    "rights.debt.deferral.recargos": {
        "es": {
            "short_title": "Deuda tributaria: aplazamiento, fraccionamiento y recargos",
            "question": "Revise si la regla distingue correctamente recargos por presentación fuera de plazo, aplazamiento/fraccionamiento y exención de garantía.",
            "why": "Mezclar recargo, intereses, aplazamiento y garantía puede llevar a prometer una facilidad que no procede o a perder una vía útil.",
            "law": "Base a revisar: Ley General Tributaria; Reglamento General de Recaudación; Orden HFP/311/2023 sobre el umbral conjunto de 50.000 euros sin garantía.",
            "verify": [
                "Que el umbral de 50.000 euros se trate como importe conjunto cuando corresponda.",
                "Que recargo e intereses no se presenten como lo mismo.",
                "Que la regla pida fechas, deuda, periodo y notificación antes de recomendar una vía.",
            ],
            "boundary": "No se concede un aplazamiento ni se calcula la deuda final. Se valida la ruta y las condiciones de revisión.",
            "expected": "Marque «Confirmar tal cual» si el umbral, la distinción de conceptos y las fuentes son correctas; si no, indique la condición a corregir.",
        },
        "ru": {
            "short_title": "Налоговый долг: отсрочка, рассрочка и надбавки",
            "question": "Проверьте, различает ли правило надбавки за просроченную подачу, отсрочку/рассрочку и освобождение от гарантии.",
            "why": "Если смешать recargo, проценты, отсрочку и гарантию, пользователю можно пообещать недоступную льготу или пропустить полезный путь.",
            "law": "Правовая опора для проверки: Ley General Tributaria; Reglamento General de Recaudación; Orden HFP/311/2023 о совокупном пороге 50 000 евро без гарантии.",
            "verify": [
                "Порог 50 000 евро учитывается как совокупный, когда это требуется.",
                "Надбавка и проценты не представлены как одно и то же.",
                "Правило требует даты, сумму долга, период и уведомление до рекомендации пути.",
            ],
            "boundary": "Здесь не предоставляется отсрочка и не рассчитывается финальный долг. Проверяется маршрут и условия проверки.",
            "expected": "Нажмите «Подтвердить как есть», если порог, различие понятий и источники верны; иначе укажите условие для исправления.",
        },
        "en": {
            "short_title": "Tax debt: deferral, instalments and surcharges",
            "question": "Check whether the rule distinguishes late-filing surcharges, deferral/instalment routes and guarantee exemption.",
            "why": "Mixing surcharge, interest, deferral and guarantee may promise unavailable relief or miss a useful route.",
            "law": "Legal basis to check: General Tax Law; General Collection Regulation; Order HFP/311/2023 on the combined EUR 50,000 no-guarantee threshold.",
            "verify": [
                "The EUR 50,000 threshold is treated as a combined amount where required.",
                "Surcharge and interest are not presented as the same concept.",
                "The rule asks for dates, debt amount, period and notice before recommending a route.",
            ],
            "boundary": "This does not grant a deferral or calculate final debt. It validates the route and review conditions.",
            "expected": "Choose “Confirm as-is” if threshold, concept separation and sources are correct; otherwise state the condition to fix.",
        },
    },
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return " ".join(str(value).split())


def _short(value: str, limit: int = 260) -> str:
    value = _string(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _first_sentence(value: str, limit: int = 210) -> str:
    value = _string(value)
    if not value:
        return ""
    protected = {
        "Art.": "Art§",
        "art.": "art§",
        "No.": "No§",
        "n.º": "n§º",
    }
    for needle, replacement in protected.items():
        value = value.replace(needle, replacement)
    match = re.search(r"(?<=[.!?])\s+", value)
    if match:
        value = value[: match.start()]
    for needle, replacement in protected.items():
        value = value.replace(replacement, needle)
    return _short(value, limit)


def _domain_label(domain_id: str, lang: str) -> str:
    labels = DOMAIN_LABELS.get(domain_id, {})
    return labels.get(lang) or labels.get("en") or domain_id.replace("_", " ")


FACT_WORDS = {
    "ru": {
        "activity": "деятельность",
        "address": "адрес",
        "admin": "администратор",
        "amount": "сумма",
        "application": "заявление",
        "asset": "актив",
        "authority": "орган",
        "authorized": "уполномоченный",
        "base": "база",
        "based": "основанный",
        "block": "блок",
        "business": "бизнес",
        "calendar": "календарный",
        "certificate": "сертификат",
        "challenge": "спор",
        "change": "изменение",
        "chosen": "выбранный",
        "claim": "заявление",
        "client": "клиент",
        "clients": "клиенты",
        "competence": "компетенция",
        "contribution": "взнос",
        "counterparty": "контрагент",
        "country": "страна",
        "coverage": "покрытие",
        "critical": "критично",
        "date": "дата",
        "day": "день",
        "days": "дни",
        "debt": "долг",
        "document": "документ",
        "documents": "документы",
        "domicile": "домициль",
        "deadline": "срок",
        "economic": "экономический",
        "employee": "работник",
        "employer": "работодатель",
        "employed": "самозанятый",
        "event": "событие",
        "evidence": "доказательство",
        "eligibility": "право на применение",
        "expected": "ожидаемый",
        "expense": "расход",
        "family": "семья",
        "filing": "подача",
        "fiscal": "налоговый",
        "foreign": "иностранный",
        "form": "форма",
        "from": "из",
        "guarantee": "гарантия",
        "health": "медицинский",
        "identity": "личность",
        "immigration": "иммиграционный",
        "income": "доход",
        "insurance": "страхование",
        "interest": "интерес",
        "issued": "выданный",
        "late": "просроченный",
        "location": "местонахождение",
        "minor": "несовершеннолетний",
        "mode": "режим",
        "notice": "уведомление",
        "not": "не",
        "operation": "операция",
        "or": "или",
        "outcome": "результат",
        "period": "период",
        "place": "место",
        "professional": "профессиональный",
        "rate": "ставка",
        "procedure": "процедура",
        "property": "недвижимость",
        "remote": "удалённый",
        "remotely": "удалённо",
        "requested": "запрошенный",
        "required": "требуется",
        "review": "проверка",
        "residence": "резидентство",
        "resident": "резидент",
        "route": "маршрут",
        "scope": "охват",
        "separate": "отдельный",
        "self": "сам",
        "share": "доля",
        "signal": "признак",
        "social": "социальный",
        "source": "источник",
        "spouse": "супруг",
        "spain": "Испания",
        "spanish": "испанский",
        "status": "статус",
        "tax": "налог",
        "taxable": "налогооблагаемый",
        "taxpayer": "налогоплательщик",
        "territory": "территория",
        "threshold": "порог",
        "type": "тип",
        "unresolved": "не решено",
        "value": "стоимость",
        "visa": "виза",
        "with": "с",
        "work": "работа",
        "worker": "работник",
        "performed": "выполняется",
        "wrong": "неподходящий",
        "year": "год",
    },
    "es": {
        "activity": "actividad",
        "address": "domicilio",
        "admin": "administrador",
        "amount": "importe",
        "application": "solicitud",
        "asset": "activo",
        "authority": "administración",
        "authorized": "autorizado",
        "base": "base",
        "based": "basado",
        "block": "bloqueo",
        "business": "actividad económica",
        "calendar": "calendario",
        "certificate": "certificado",
        "challenge": "controversia",
        "change": "cambio",
        "chosen": "elegido",
        "claim": "alegación",
        "client": "cliente",
        "clients": "clientes",
        "competence": "competencia",
        "contribution": "cotización",
        "counterparty": "contraparte",
        "country": "país",
        "coverage": "cobertura",
        "critical": "crítico",
        "date": "fecha",
        "day": "día",
        "days": "días",
        "debt": "deuda",
        "document": "documento",
        "documents": "documentos",
        "domicile": "domicilio",
        "deadline": "plazo",
        "economic": "económico",
        "employee": "empleado",
        "employer": "empleador",
        "employed": "autónomo",
        "event": "hecho",
        "evidence": "prueba",
        "eligibility": "derecho de aplicación",
        "expected": "esperado",
        "expense": "gasto",
        "family": "familia",
        "filing": "presentación",
        "fiscal": "fiscal",
        "foreign": "extranjero",
        "form": "modelo",
        "from": "desde",
        "guarantee": "garantía",
        "health": "salud",
        "identity": "identidad",
        "immigration": "inmigración",
        "income": "renta",
        "insurance": "seguro",
        "interest": "interés",
        "issued": "emitido",
        "late": "tardío",
        "location": "ubicación",
        "minor": "menor",
        "mode": "modalidad",
        "notice": "notificación",
        "not": "no",
        "operation": "operación",
        "or": "o",
        "outcome": "resultado",
        "period": "periodo",
        "place": "lugar",
        "professional": "profesional",
        "rate": "tipo",
        "procedure": "procedimiento",
        "property": "inmueble",
        "remote": "remoto",
        "remotely": "en remoto",
        "requested": "solicitado",
        "required": "requerido",
        "review": "revisión",
        "residence": "residencia",
        "resident": "residente",
        "route": "ruta",
        "scope": "alcance",
        "separate": "separado",
        "self": "propio",
        "share": "porcentaje",
        "signal": "señal",
        "social": "social",
        "source": "fuente",
        "spouse": "cónyuge",
        "spain": "España",
        "spanish": "español",
        "status": "estado",
        "tax": "impuesto",
        "taxable": "hecho imponible",
        "taxpayer": "contribuyente",
        "territory": "territorio",
        "threshold": "umbral",
        "type": "tipo",
        "unresolved": "sin resolver",
        "value": "valor",
        "visa": "visado",
        "with": "con",
        "work": "trabajo",
        "worker": "trabajador",
        "performed": "realizado",
        "wrong": "incorrecto",
        "year": "año",
    },
}


FACT_LABELS = {
    "tax_territory": {
        "es": "territorio fiscal aplicable",
        "ru": "применимая налоговая территория",
        "en": "applicable tax territory",
    },
    "taxpayer_type_or_status": {
        "es": "tipo y estado fiscal del contribuyente",
        "ru": "тип и налоговый статус налогоплательщика",
        "en": "taxpayer type and tax status",
    },
    "tax_period": {"es": "periodo fiscal", "ru": "налоговый период", "en": "tax period"},
    "taxable_event_or_income_type": {
        "es": "hecho imponible o tipo de renta",
        "ru": "налогооблагаемое событие или тип дохода",
        "en": "taxable event or income type",
    },
    "wrong_taxpayer_type_or_status_for_rule": {
        "es": "tipo de contribuyente incompatible con esta regla",
        "ru": "тип или статус налогоплательщика не подходит для правила",
        "en": "taxpayer type or status incompatible with this rule",
    },
    "territory_or_period_unresolved": {
        "es": "territorio o periodo todavía no resuelto",
        "ru": "территория или период ещё не определены",
        "en": "territory or period still unresolved",
    },
    "prior_spanish_tax_residence_periods": {
        "es": "periodos previos con residencia fiscal española",
        "ru": "предыдущие периоды испанского налогового резидентства",
        "en": "prior Spanish tax residence periods",
    },
    "qualifying_displacement_cause": {
        "es": "causa válida de desplazamiento a España",
        "ru": "допустимое основание переезда в Испанию",
        "en": "qualifying reason for moving to Spain",
    },
    "modelo_149_trigger_date": {
        "es": "fecha que abre el plazo del Modelo 149",
        "ru": "дата, запускающая срок Modelo 149",
        "en": "date that starts the Modelo 149 window",
    },
    "has_spanish_permanent_establishment": {
        "es": "existencia de establecimiento permanente en España",
        "ru": "наличие постоянного представительства в Испании",
        "en": "Spanish permanent establishment status",
    },
    "immigration_route": {
        "es": "tipo de visado o autorización de residencia",
        "ru": "тип визы или разрешения на проживание",
        "en": "visa or residence-authorization route",
    },
    "work_performed_remotely_from_spain": {
        "es": "trabajo realizado en remoto desde España",
        "ru": "работа, выполняемая удалённо из Испании",
        "en": "work performed remotely from Spain",
    },
    "work_mode": {
        "es": "modalidad de trabajo: empleado, profesional, administrador o mixta",
        "ru": "формат работы: работник, профессионал, администратор или смешанный вариант",
        "en": "work mode: employee, professional, director or mixed",
    },
    "employee_route_with_spanish_employer": {
        "es": "ruta de empleado con empleador español",
        "ru": "маршрут работника с испанским работодателем",
        "en": "employee route with Spanish employer",
    },
    "self_employed_spanish_client_share_percent": {
        "es": "porcentaje de clientes españoles en actividad profesional",
        "ru": "доля испанских клиентов в профессиональной деятельности",
        "en": "Spanish-client share for professional activity",
    },
    "tax_territory_signal": {
        "es": "señal del territorio fiscal",
        "ru": "признак налоговой территории",
        "en": "tax territory signal",
    },
    "fiscal_domicile_or_operation_place": {
        "es": "domicilio fiscal o lugar de la operación",
        "ru": "налоговый адрес или место операции",
        "en": "tax domicile or place of operation",
    },
    "tax_domain": {
        "es": "materia tributaria afectada",
        "ru": "налоговая область вопроса",
        "en": "tax domain affected",
    },
    "territory_already_resolved_to_other_authority": {
        "es": "territorio ya atribuido a otra administración",
        "ru": "территория уже отнесена к другой администрации",
        "en": "territory already assigned to another authority",
    },
}


RISK_CODE_LABELS = {
    "modelo_149_deadline_critical": {
        "es": "el plazo del Modelo 149 es crítico",
        "ru": "срок Modelo 149 критичен",
        "en": "the Modelo 149 deadline is critical",
    },
    "art93_not_final_eligibility": {
        "es": "esta tarjeta no confirma definitivamente el derecho al Art. 93",
        "ru": "эта карточка не подтверждает окончательное право на Art. 93",
        "en": "this card does not finally confirm Art. 93 eligibility",
    },
    "model_202_threshold_method_required": {
        "es": "hay que confirmar método y umbrales antes de hablar del Modelo 202",
        "ru": "перед выводом по Modelo 202 нужно подтвердить метод и пороги",
        "en": "method and thresholds must be confirmed before a Modelo 202 conclusion",
    },
    "foral_allocation_threshold_review": {
        "es": "el umbral foral de reparto debe verificarse en el artículo correcto",
        "ru": "foral-порог распределения нужно сверить с правильной статьёй",
        "en": "the foral allocation threshold must be checked against the correct article",
    },
    "digital_nomad_tax_not_automatic": {
        "es": "el visado de teletrabajo no decide automáticamente la fiscalidad",
        "ru": "виза digital nomad не решает налоги автоматически",
        "en": "a digital-nomad visa does not automatically decide tax treatment",
    },
    "social_security_separate_review": {
        "es": "la Seguridad Social requiere revisión separada",
        "ru": "соцстрахование требует отдельной проверки",
        "en": "social security requires a separate review",
    },
    "deferral_exclusion_check_required": {
        "es": "hay que descartar deudas no aplazables antes de recomendar aplazamiento",
        "ru": "перед рекомендацией отсрочки нужно исключить неотсрочиваемые долги",
        "en": "non-deferrable debts must be ruled out before recommending deferral",
    },
    "recargo_vs_sanction_needs_notice_status": {
        "es": "recargo y sanción dependen del estado de la notificación",
        "ru": "надбавка и санкция зависят от статуса уведомления",
        "en": "surcharge and sanction depend on notice status",
    },
}


def _risk_public_text(code: str, severity: str, lang: str) -> str:
    label = RISK_CODE_LABELS.get(code, {}).get(lang)
    if not label:
        label = _humanize_fact(code, lang)
    severity_labels = {
        "critical": {"es": "crítico", "ru": "критично", "en": "critical"},
        "high": {"es": "alto riesgo", "ru": "высокий риск", "en": "high risk"},
        "medium": {"es": "riesgo medio", "ru": "средний риск", "en": "medium risk"},
    }
    sev = severity_labels.get(severity, {}).get(lang) or severity.replace("_", " ")
    templates = {
        "es": "Revisar con cautela: {label}" + (f" ({sev})." if sev else "."),
        "ru": "Проверить осторожно: {label}" + (f" ({sev})." if sev else "."),
        "en": "Review with caution: {label}" + (f" ({sev})." if sev else "."),
    }
    return templates[lang].format(label=label)


def _humanize_fact(fact: str, lang: str) -> str:
    fact = _string(fact)
    labels = FACT_LABELS.get(fact)
    if labels:
        return labels.get(lang) or labels.get("en") or fact
    words = re.split(r"[_\s]+", fact)
    if lang == "en":
        return " ".join(words)
    dictionary = FACT_WORDS.get(lang, {})
    translated = [dictionary.get(word, word) for word in words if word]
    return " ".join(translated)


def _format_value(value: Any, lang: str = "en") -> str:
    if isinstance(value, bool):
        return {
            "es": "sí" if value else "no",
            "ru": "да" if value else "нет",
            "en": "yes" if value else "no",
        }[lang]
    if isinstance(value, (int, float)):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, list):
        return ", ".join(_format_value(item, lang) for item in value[:5])
    text = _string(value)
    translations = {
        "calendar_year": {"es": "año natural", "ru": "календарный год", "en": "calendar year"},
        "move_year_plus_five_following_tax_periods": {
            "es": "año de traslado y cinco periodos fiscales siguientes",
            "ru": "год переезда и пять следующих налоговых периодов",
            "en": "move year plus five following tax periods",
        },
        "Ley Organica 1/2025 disposicion final vigesimoprimera": {
            "es": "Ley Orgánica 1/2025, disposición final vigesimoprimera",
            "ru": "Ley Orgánica 1/2025, disposición final vigesimoprimera",
            "en": "Organic Law 1/2025, final provision twenty-first",
        },
    }
    if text in translations:
        return translations[text].get(lang) or translations[text]["en"]
    return text.replace("_", " ")


def _format_form_id(value: str) -> str:
    value = _string(value)
    match = re.fullmatch(r"modelo_?(\d+[A-Za-z]?)", value, flags=re.IGNORECASE)
    if match:
        return f"Modelo {match.group(1)}"
    return value.replace("_", " ")


def _value_label(key: str, lang: str) -> str:
    labels = {
        "lookback_tax_periods_without_spanish_residence": {
            "es": "periodos previos sin residencia fiscal española",
            "ru": "предыдущие периоды без испанского налогового резидентства",
            "en": "prior periods without Spanish tax residence",
        },
        "spanish_client_share_limit_for_professional_route_percent": {
            "es": "límite de clientes españoles para la ruta profesional",
            "ru": "лимит доли испанских клиентов для профессионального маршрута",
            "en": "Spanish-client limit for the professional route",
        },
        "modelo_149_option_deadline_months": {
            "es": "plazo de opción del Modelo 149, meses",
            "ru": "срок выбора режима через Modelo 149, месяцев",
            "en": "Modelo 149 option deadline, months",
        },
        "initial_threshold_eur": {"es": "umbral inicial", "ru": "начальный порог", "en": "initial threshold"},
        "day_threshold": {"es": "umbral de días", "ru": "порог дней", "en": "day threshold"},
        "period_basis": {"es": "base temporal", "ru": "основа периода", "en": "period basis"},
        "new_investor_route_closed_from": {
            "es": "cierre de nuevas solicitudes de inversor desde",
            "ru": "закрытие новых investor-route заявлений с",
            "en": "new investor route closed from",
        },
        "repeal_instrument": {"es": "norma derogatoria", "ru": "отменяющий акт", "en": "repeal instrument"},
        "repeat_increase_threshold_eur": {
            "es": "umbral de incremento para repetir declaración",
            "ru": "порог прироста для повторной декларации",
            "en": "repeat filing increase threshold",
        },
        "counterparty_threshold_eur": {
            "es": "umbral por contraparte",
            "ru": "порог по контрагенту",
            "en": "counterparty threshold",
        },
        "deferral_guarantee_exemption_threshold_eur_en_conjunto": {
            "es": "umbral conjunto sin garantía",
            "ru": "совокупный порог без гарантии",
            "en": "combined no-guarantee threshold",
        },
        "modelo_232_same_person_or_entity_threshold_eur": {
            "es": "umbral Modelo 232 para una misma persona o entidad",
            "ru": "порог Modelo 232 для одного лица или организации",
            "en": "Modelo 232 same person/entity threshold",
        },
        "modelo_232_specific_operations_threshold_eur": {
            "es": "umbral Modelo 232 para operaciones específicas",
            "ru": "порог Modelo 232 для специальных операций",
            "en": "Modelo 232 specific operations threshold",
        },
        "navarra_iva_allocation_threshold_eur_current_boe_pdf": {
            "es": "umbral IVA Navarra verificado en BOE",
            "ru": "порог IVA Navarra, проверенный в BOE",
            "en": "Navarra IVA threshold checked in BOE",
        },
        "pais_vasco_iva_allocation_threshold_eur_current_boe_pdf": {
            "es": "umbral IVA País Vasco verificado en BOE",
            "ru": "порог IVA País Vasco, проверенный в BOE",
            "en": "Basque Country IVA threshold checked in BOE",
        },
    }
    if key in labels:
        return labels[key].get(lang) or labels[key]["en"]
    return ""


def _public_scope(rule: dict[str, Any], recommendation: dict[str, Any], structured_values: dict[str, Any], lang: str) -> str:
    display = recommendation.get("display_text") or {}
    localized = _first_sentence(display.get(lang) or "")
    if localized:
        return localized
    for key in ("fiscal_scope", "procedure_scope", "authority_scope", "scope", "route"):
        if structured_values.get(key):
            return _string(structured_values[key])
    return _first_sentence(recommendation.get("summary") or rule.get("scenario") or rule.get("rule_id"))


def _condition_items(recommendation: dict[str, Any], lang: str) -> tuple[list[str], list[str]]:
    conditions = recommendation.get("conditions") or {}
    exclusions = recommendation.get("exclusions") or {}
    requires = []
    blockers = []
    for item in _as_list(conditions.get("requires"))[:5]:
        if isinstance(item, dict) and item.get("fact"):
            requires.append(_humanize_fact(item["fact"], lang))
    for item in _as_list(exclusions.get("blocks"))[:4]:
        if isinstance(item, dict) and item.get("fact"):
            blockers.append(_humanize_fact(item["fact"], lang))
    return requires, blockers


def _source_public(source: dict[str, Any], lang: str) -> dict[str, str]:
    title = source.get("support_anchor") or source.get("title") or source.get("source_id")
    meta = " · ".join(item for item in (source.get("jurisdiction"), source.get("last_checked")) if item)
    if "unverifiable" in source.get("review_status", ""):
        notes = {
            "es": "Abrir manualmente: la comprobación automática no pudo verificar esta fuente.",
            "ru": "Открыть вручную: автоматическая проверка не смогла подтвердить этот источник.",
            "en": "Open manually: the automatic check could not verify this source.",
        }
        support = {"es": "requiere revisión", "ru": "нужна проверка", "en": "needs review"}
    elif source.get("support_state") == "yes":
        notes = {
            "es": "Usar como soporte oficial de la regla indicada.",
            "ru": "Использовать как официальную опору для проверяемого правила.",
            "en": "Use as official support for the reviewed rule.",
        }
        support = {"es": "confirma", "ru": "подтверждает", "en": "supports"}
    else:
        notes = {
            "es": "Revisar antes de aprobar: el soporte no está marcado como confirmado.",
            "ru": "Проверить до одобрения: источник не отмечен как подтверждённый.",
            "en": "Review before approval: support is not marked as confirmed.",
        }
        support = {"es": "no confirmado", "ru": "не подтверждён", "en": "not confirmed"}
    return {
        "title": _string(title),
        "meta": meta,
        "note": notes[lang],
        "support": support[lang],
    }


def _legal_basis(sources: list[dict[str, Any]], lang: str) -> str:
    anchors = [_string(source.get("support_anchor") or source.get("title")) for source in sources[:5]]
    anchors = [anchor for anchor in anchors if anchor]
    if not anchors:
        return {
            "es": "No hay fuente oficial suficiente en la tarjeta; el gestor debe marcarlo antes de aprobar.",
            "ru": "В карточке нет достаточного официального источника; гестор должен отметить это до одобрения.",
            "en": "The card does not contain sufficient official source support; the gestor must flag this before approval.",
        }[lang]
    joined = "; ".join(anchors)
    prefix = {
        "es": "Base a revisar",
        "ru": "Правовая опора для проверки",
        "en": "Basis to check",
    }[lang]
    return f"{prefix}: {joined}."


def _generic_verify_items(
    rule: dict[str, Any],
    recommendation: dict[str, Any],
    structured_values: dict[str, Any],
    sources: list[dict[str, Any]],
    lang: str,
) -> list[str]:
    forms = [_format_form_id(item) for item in _as_list((recommendation.get("parameters") or {}).get("form_ids")) if _string(item)]
    requires, blockers = _condition_items(recommendation, lang)
    items: list[str] = []
    if forms:
        items.append(
            {
                "es": "Modelo(s) afectados: ",
                "ru": "Затронутые формы: ",
                "en": "Affected form(s): ",
            }[lang]
            + ", ".join(forms)
        )
    for item in requires[:3]:
        items.append({"es": "Confirmar: ", "ru": "Подтвердить: ", "en": "Confirm: "}[lang] + item + ".")
    for item in blockers[:2]:
        items.append({"es": "Descartar bloqueo: ", "ru": "Исключить блокер: ", "en": "Rule out blocker: "}[lang] + item + ".")
    skipped_keys = {
        "source_refresh_required_before_final_answer",
        "gestor_review_required",
        "requires_verified_facts_before_amounts",
        "fiscal_scope",
        "procedure_scope",
        "authority_scope",
        "scope",
        "route",
        "calculation_policy",
    }
    for key, value in list(structured_values.items())[:8]:
        if key in {"source_refresh_required_before_final_answer", "gestor_review_required", "requires_verified_facts_before_amounts"}:
            continue
        if key in skipped_keys:
            continue
        label = _value_label(key, lang)
        if label:
            items.append(f"{label}: {_format_value(value, lang)}.")
    if any(source.get("support_state") != "yes" for source in sources):
        items.append(
            {
                "es": "Hay fuentes que requieren revisión manual antes de aprobar.",
                "ru": "Есть источники, которые нужно открыть вручную перед одобрением.",
                "en": "Some sources require manual review before approval.",
            }[lang]
        )
    return items[:7] or [
        {
            "es": "Comprobar hechos del cliente, periodo, territorio y documentos antes de aprobar.",
            "ru": "Сверить факты клиента, период, территорию и документы до одобрения.",
            "en": "Check client facts, period, territory and documents before approval.",
        }[lang]
    ]


def _client_request_items(
    recommendation: dict[str, Any], structured_values: dict[str, Any], domain_id: str, lang: str
) -> list[str]:
    base = {
        "es": ["Datos del contribuyente y periodo fiscal.", "Documentos que prueban la operación o situación."],
        "ru": ["Данные налогоплательщика и налоговый период.", "Документы, подтверждающие операцию или ситуацию."],
        "en": ["Taxpayer details and tax period.", "Documents proving the transaction or situation."],
    }[lang]
    if structured_values.get("requires_verified_facts_before_amounts") or structured_values.get("gestor_review_required"):
        base.append(
            {
                "es": "Confirmación del gestor antes de calcular importes o presentar modelos.",
                "ru": "Подтверждение гестора до расчёта сумм или подачи форм.",
                "en": "Gestor confirmation before calculating amounts or filing forms.",
            }[lang]
        )
    if domain_id == "inbound_immigration_tax":
        base.append(
            {
                "es": "Fechas de llegada, trabajo, residencia y cobertura social.",
                "ru": "Даты приезда, работы, резидентства и социального покрытия.",
                "en": "Arrival, work, residence and social-coverage dates.",
            }[lang]
        )
    if domain_id == "territorial_jurisdiction":
        base.append(
            {
                "es": "Lugar de operaciones, domicilio fiscal y administración competente.",
                "ru": "Место операций, налоговый адрес и компетентная администрация.",
                "en": "Place of operations, tax domicile and competent authority.",
            }[lang]
        )
    return base[:5]


def _build_briefs(
    rule: dict[str, Any],
    recommendation: dict[str, Any],
    domain_id: str,
    structured_values: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rule_id = _string(rule.get("rule_id"))
    manual = MANUAL_BRIEFS.get(rule_id)
    briefs: dict[str, dict[str, Any]] = {}
    for lang in LANGS:
        if manual and lang in manual:
            brief = dict(manual[lang])
            brief["request"] = _client_request_items(recommendation, structured_values, domain_id, lang)
            brief["source_intro"] = brief.get("law") or _legal_basis(sources, lang)
            briefs[lang] = brief
            continue
        scope = _public_scope(rule, recommendation, structured_values, lang)
        domain = _domain_label(domain_id, lang)
        why = DOMAIN_PURPOSES.get(domain_id, {}).get(lang) or DOMAIN_PURPOSES.get(domain_id, {}).get("en") or ""
        if (recommendation.get("logic_profile") or {}).get("high_stakes"):
            why = {
                "es": f"Es una revisión sensible: {why}",
                "ru": f"Это чувствительная проверка: {why}",
                "en": f"This is a sensitive review: {why}",
            }[lang]
        else:
            why = {
                "es": f"Sirve para {why}",
                "ru": f"Это нужно, чтобы {why}",
                "en": f"It is needed {why}",
            }[lang]
        question = {
            "es": f"Revise si la regla trata correctamente esta tarea de {domain}: {scope}",
            "ru": f"Проверьте, правильно ли правило обрабатывает задачу из области «{domain}»: {scope}",
            "en": f"Check whether the rule correctly handles this {domain} task: {scope}",
        }[lang]
        boundary = {
            "es": "Pre-Gestor puede orientar el caso y pedir datos, pero no debe calcular importes finales ni presentar modelos sin revisión del gestor.",
            "ru": "Pre-Gestor может сориентировать по случаю и запросить данные, но не должен считать финальные суммы или подавать формы без проверки гестора.",
            "en": "Pre-Gestor may orient the case and request data, but must not calculate final amounts or file forms without gestor review.",
        }[lang]
        expected = {
            "es": "Elija el resultado, confirme si las fuentes sostienen la regla y escriba una corrección obligatoria si algo debe cambiar antes de publicarse.",
            "ru": "Выберите итог, подтвердите поддержку источниками и напишите обязательную правку, если что-то нужно изменить до публикации.",
            "en": "Choose the outcome, confirm source support and write the required fix if anything must change before publication.",
        }[lang]
        briefs[lang] = {
            "short_title": scope or rule_id,
            "question": question,
            "why": why,
            "law": _legal_basis(sources, lang),
            "verify": _generic_verify_items(rule, recommendation, structured_values, sources, lang),
            "request": _client_request_items(recommendation, structured_values, domain_id, lang),
            "boundary": boundary,
            "expected": expected,
            "source_intro": _legal_basis(sources, lang),
        }
    return briefs


def _load_source_registry(data_dir: Path) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for path in sorted((data_dir / "source_registry").glob("*.yaml")):
        raw = _load_yaml(path)
        for source_id, source in (raw.get("sources") or {}).items():
            sources[str(source_id)] = dict(source or {})
    return sources


def _source_from_claim(source_id: str, claim: dict[str, Any] | None, registry: dict[str, dict[str, Any]]) -> dict[str, Any]:
    registered = registry.get(source_id, {})
    claim = claim or {}
    source = {
        "source_id": source_id,
        "title": _string(registered.get("title") or claim.get("support_anchor") or source_id),
        "url": _string(claim.get("source_url") or registered.get("source_url")),
        "support_anchor": _string(claim.get("support_anchor")),
        "claim": _string(claim.get("claim")),
        "support_state": _string(claim.get("claim_supported_by_source") or "unknown"),
        "last_checked": _string(claim.get("last_checked") or registered.get("last_checked")),
        "review_status": _string(claim.get("review_status") or registered.get("review_status")),
        "jurisdiction": _string(claim.get("jurisdiction") or registered.get("jurisdiction")),
    }
    source["public"] = {lang: _source_public(source, lang) for lang in LANGS}
    return source


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return "unknown"


def _build_dataset(data_dir: Path, source_label: str, source_commit: str) -> dict[str, Any]:
    registry = _load_source_registry(data_dir)
    rules: list[dict[str, Any]] = []
    rule_dir = data_dir / "rule_packs"
    for pack_path in sorted(rule_dir.glob("*.yaml")):
        pack = _load_yaml(pack_path)
        domain_id = _string(pack.get("domain_id"))
        for rule in _as_list(pack.get("rules")):
            recommendation = rule.get("recommendation") or {}
            display = recommendation.get("display_text") or {}
            logic = recommendation.get("logic_profile") or {}
            params = recommendation.get("parameters") or {}
            structured_values = params.get("structured_values") or {}
            claims_by_id = {
                _string(claim.get("source_id")): claim
                for claim in _as_list(recommendation.get("source_claims"))
                if isinstance(claim, dict)
            }
            source_ids = [_string(item) for item in _as_list(recommendation.get("source_ids"))]
            sources = [_source_from_claim(source_id, claims_by_id.get(source_id), registry) for source_id in source_ids]
            rule_id = _string(rule.get("rule_id"))
            focus = FOCUS_QUEUE.get(rule_id)
            risk_flags = [
                {
                    "code": _string(item.get("code")),
                    "severity": _string(item.get("severity")),
                    "message": _string(item.get("message")),
                    "public": {
                        lang: _risk_public_text(_string(item.get("code")), _string(item.get("severity")), lang)
                        for lang in LANGS
                    },
                }
                for item in _as_list(recommendation.get("risk_flags"))
                if isinstance(item, dict)
            ]
            tags = []
            if focus:
                tags.append("gestor_queue")
            if logic.get("high_stakes"):
                tags.append("high_stakes")
            if any(source.get("support_state") != "yes" for source in sources):
                tags.append("source_attention")
            if any("unverifiable" in source.get("review_status", "") for source in sources):
                tags.append("unverifiable_by_fetch")
            briefs = _build_briefs(rule, recommendation, domain_id, structured_values, sources)
            rules.append(
                {
                    "index": len(rules) + 1,
                    "type": "rule",
                    "rule_id": rule_id,
                    "rule_pack_id": _string(pack.get("rule_pack_id")),
                    "pack_file": pack_path.name,
                    "domain_id": domain_id,
                    "domain_labels": {
                        lang: _domain_label(domain_id, lang)
                        for lang in LANGS
                    },
                    "domain_label": _domain_label(domain_id, "en"),
                    "scenario": _string(rule.get("scenario")),
                    "priority": rule.get("priority"),
                    "confidence": rule.get("confidence"),
                    "gestor_review_state": _string(rule.get("gestor_review_state") or "unreviewed"),
                    "high_stakes": bool(logic.get("high_stakes")),
                    "rule_type": _string(logic.get("rule_type")),
                    "valid_from": _string((rule.get("triggers") or {}).get("period_scope", {}).get("valid_from") or pack.get("valid_from")),
                    "valid_until": _string((rule.get("triggers") or {}).get("period_scope", {}).get("valid_until") or pack.get("valid_until")),
                    "texts": {
                        "es": {
                            "title": _short(display.get("es") or recommendation.get("summary")),
                            "summary": _string(display.get("es") or recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                        "ru": {
                            "title": _short(display.get("ru") or recommendation.get("summary")),
                            "summary": _string(display.get("ru") or recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                        "en": {
                            "title": _short(recommendation.get("summary")),
                            "summary": _string(recommendation.get("summary")),
                            "practical": _string(recommendation.get("practical_answer")),
                        },
                    },
                    "briefs": briefs,
                    "focus_question": focus,
                    "next_actions": [_string(item) for item in _as_list(recommendation.get("next_actions"))],
                    "evidence_needed": [_string(item) for item in _as_list(recommendation.get("evidence_needed"))],
                    "open_questions": [_string(item) for item in _as_list(recommendation.get("open_questions"))],
                    "risk_flags": risk_flags,
                    "structured_values": structured_values,
                    "forms": _as_list(params.get("form_ids")),
                    "sources": sources,
                    "tags": tags,
                    "reward_eur": 1,
                }
            )
    return {
        "schema": "pre_gestor_public_review_console.v2",
        "dataset_id": "pre-gestor-a1-2026-06-19-legal-audit",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "label": source_label,
            "commit": source_commit,
            "rule_count": len(rules),
            "review_unit_credit_eur": 1,
        },
        "stats": {
            "rules_total": len(rules),
            "gestor_queue": sum(1 for rule in rules if "gestor_queue" in rule["tags"]),
            "source_attention": sum(1 for rule in rules if "source_attention" in rule["tags"]),
            "high_stakes": sum(1 for rule in rules if rule["high_stakes"]),
        },
        "rules": rules,
    }


def _page_template(dataset_json: str, generated_at: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Pre-Gestor expert review console for Spanish fiscal rules.">
  <link rel="icon" href="../favicon.ico">
  <title>Pre-Gestor Expert Review · Occam</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-2: #f8fafc;
      --ink: #172033;
      --muted: #667085;
      --faint: #98a2b3;
      --line: #d9e0ea;
      --line-soft: #e8edf3;
      --navy: #142b51;
      --teal: #0f766e;
      --teal-soft: #e7f5f2;
      --burgundy: #9f174f;
      --burgundy-soft: #fde8f1;
      --amber: #b45309;
      --amber-soft: #fff4df;
      --red: #b42318;
      --red-soft: #feeceb;
      --green: #047857;
      --green-soft: #e8f7ee;
      --violet: #5b4bb2;
      --violet-soft: #eeecfb;
      --shadow: 0 18px 48px rgba(20, 43, 81, .10);
      --shadow-sm: 0 6px 20px rgba(20, 43, 81, .07);
      --radius: 8px;
      --font: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: var(--font);
      color: var(--ink);
      background:
        linear-gradient(180deg, #eef2f7 0, #f7f9fb 280px, var(--bg) 100%);
      -webkit-font-smoothing: antialiased;
      line-height: 1.5;
    }}
    a {{ color: var(--teal); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    button, input, textarea, select {{ font: inherit; }}
    button {{ cursor: pointer; }}
    .app {{ max-width: 1540px; margin: 0 auto; padding: 20px; }}
    .topbar {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }}
    .brandline {{ display: flex; gap: 12px; align-items: center; min-width: 0; }}
    .mark {{
      width: 42px;
      height: 42px;
      border-radius: var(--radius);
      display: grid;
      place-items: center;
      background: var(--navy);
      color: white;
      font-weight: 800;
      letter-spacing: .02em;
      flex: 0 0 auto;
    }}
    h1 {{ margin: 0; font-size: 24px; line-height: 1.1; letter-spacing: 0; }}
    .subtitle {{ margin: 5px 0 0; color: var(--muted); max-width: 980px; font-size: 14px; }}
    .toolbar {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }}
    .segmented, .compact-group {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
    }}
    .segmented button, .btn, .chip, .choice {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 7px;
      min-height: 36px;
      padding: 8px 11px;
      font-weight: 700;
      font-size: 13px;
    }}
    .segmented button.active, .chip.active {{
      background: var(--navy);
      border-color: var(--navy);
      color: #fff;
    }}
    .btn.primary {{ background: var(--teal); border-color: var(--teal); color: #fff; }}
    .btn.subtle {{ background: var(--panel-2); }}
    .btn:disabled {{ opacity: .45; cursor: not-allowed; }}
    .meta-strip {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .metric {{
      background: rgba(255,255,255,.92);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      box-shadow: var(--shadow-sm);
      min-height: 78px;
    }}
    .metric b {{ display: block; font-size: 24px; line-height: 1; margin-bottom: 7px; font-variant-numeric: tabular-nums; }}
    .metric span {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }}
    .layout {{
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr) 360px;
      gap: 14px;
      align-items: start;
    }}
    .panel {{
      background: rgba(255,255,255,.96);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px;
      border-bottom: 1px solid var(--line-soft);
    }}
    .panel-title {{ font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }}
    .pad {{ padding: 14px; }}
    .field {{ display: grid; gap: 6px; margin-bottom: 12px; }}
    label {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }}
    input, textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: #fff;
      color: var(--ink);
      padding: 10px 11px;
      min-height: 40px;
    }}
    textarea {{ min-height: 112px; resize: vertical; line-height: 1.45; }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .chip {{ min-height: 32px; padding: 6px 9px; }}
    .queue-list {{ max-height: calc(100vh - 318px); overflow: auto; border-top: 1px solid var(--line-soft); }}
    .queue-row {{
      width: 100%;
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr) auto;
      gap: 9px;
      align-items: center;
      border: 0;
      border-bottom: 1px solid var(--line-soft);
      background: transparent;
      padding: 10px 12px;
      text-align: left;
      color: var(--ink);
    }}
    .queue-row:hover {{ background: #f3f7fb; }}
    .queue-row.active {{ background: #eaf5f2; }}
    .queue-row strong {{ display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 13px; }}
    .queue-row small {{ display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--muted); font-size: 12px; }}
    .index-dot {{
      width: 24px;
      height: 24px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: var(--panel-2);
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
    }}
    .status-dot {{ width: 12px; height: 12px; border-radius: 999px; background: #cbd5e1; }}
    .status-dot.verified {{ background: var(--green); }}
    .status-dot.needs_fix {{ background: var(--amber); }}
    .status-dot.reject {{ background: var(--red); }}
    .status-dot.out_of_scope {{ background: var(--violet); }}
    .workspace-head {{ padding: 18px 20px 14px; border-bottom: 1px solid var(--line-soft); }}
    .rule-kicker {{ color: var(--muted); font: 700 12px var(--mono); overflow-wrap: anywhere; }}
    .rule-title {{ margin: 8px 0 12px; font-size: 24px; line-height: 1.2; letter-spacing: 0; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 5px 9px;
      font-size: 12px;
      font-weight: 800;
      background: var(--panel-2);
      color: var(--muted);
      border: 1px solid var(--line-soft);
    }}
    .badge.queue {{ background: var(--burgundy-soft); color: var(--burgundy); border-color: #f7c7dc; }}
    .badge.high {{ background: var(--red-soft); color: var(--red); border-color: #f7c2bf; }}
    .badge.source {{ background: var(--amber-soft); color: var(--amber); border-color: #f4d18f; }}
    .badge.ok {{ background: var(--green-soft); color: var(--green); border-color: #b7e4c8; }}
    .content-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(260px, .95fr);
      gap: 14px;
      padding: 16px;
    }}
    .sectionbox {{
      border: 1px solid var(--line-soft);
      background: #fff;
      border-radius: var(--radius);
      padding: 14px;
    }}
    .sectionbox h2, .sectionbox h3 {{
      margin: 0 0 9px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
    }}
    .sectionbox p {{ margin: 0; color: #303a48; }}
    .source-intro {{ margin-bottom: 12px !important; }}
    .list {{ margin: 0; padding-left: 18px; color: #303a48; }}
    .list li {{ margin: 6px 0; }}
    .source-list {{ display: grid; gap: 9px; }}
    .source {{
      border: 1px solid var(--line-soft);
      background: #fff;
      border-radius: var(--radius);
      padding: 11px;
    }}
    .source-top {{ display: flex; gap: 10px; justify-content: space-between; align-items: start; }}
    .source a {{ font-weight: 800; overflow-wrap: anywhere; }}
    .source small {{ display: block; color: var(--muted); margin-top: 4px; overflow-wrap: anywhere; }}
    .claim-text {{ margin-top: 8px; color: #475467; font-size: 13px; }}
    .technical-box summary {{ cursor: pointer; color: var(--muted); font-weight: 800; }}
    .tech-grid {{
      display: grid;
      grid-template-columns: minmax(120px, .25fr) minmax(0, 1fr);
      gap: 6px 12px;
      margin: 12px 0 0;
      font-size: 12px;
      color: #475467;
    }}
    .tech-grid dt {{ color: var(--muted); font-weight: 800; }}
    .tech-grid dd {{ margin: 0; overflow-wrap: anywhere; }}
    .mini {{ font: 700 11px var(--mono); color: var(--muted); }}
    .decision {{ position: sticky; top: 14px; }}
    .progressbar {{ height: 9px; background: #e5eaf0; overflow: hidden; border-radius: 999px; }}
    .progressbar div {{ height: 100%; width: 0; background: linear-gradient(90deg, var(--teal), var(--burgundy)); transition: width .2s ease; }}
    .credit {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin: 12px 0;
      padding: 12px;
      border: 1px solid #cce4dd;
      border-radius: var(--radius);
      background: var(--teal-soft);
    }}
    .credit b {{ font-size: 26px; font-variant-numeric: tabular-nums; }}
    .choice-group {{ display: grid; gap: 8px; margin-bottom: 14px; }}
    .choice-label {{ font-size: 12px; color: var(--muted); font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }}
    .choice-row {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }}
    .choice {{ min-height: 42px; text-align: left; }}
    .choice.selected {{ color: #fff; border-color: transparent; }}
    .choice.verified.selected, .choice.yes.selected {{ background: var(--green); }}
    .choice.needs_fix.selected, .choice.partial.selected, .choice.unclear.selected {{ background: var(--amber); }}
    .choice.reject.selected, .choice.no.selected {{ background: var(--red); }}
    .choice.out_of_scope.selected, .choice.na.selected {{ background: var(--violet); }}
    .actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .actions .wide {{ grid-column: 1 / -1; }}
    .empty {{ padding: 28px; color: var(--muted); text-align: center; }}
    .toast {{
      position: fixed;
      right: 18px;
      bottom: 18px;
      background: var(--navy);
      color: #fff;
      padding: 12px 14px;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      transform: translateY(12px);
      opacity: 0;
      pointer-events: none;
      transition: .18s ease;
      max-width: 380px;
      z-index: 20;
    }}
    .toast.show {{ opacity: 1; transform: translateY(0); }}
    @media (max-width: 1180px) {{
      .layout {{ grid-template-columns: 300px minmax(0, 1fr); }}
      .decision {{ position: static; grid-column: 1 / -1; }}
      .meta-strip {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      .app {{ padding: 12px; }}
      .topbar, .layout, .content-grid {{ grid-template-columns: 1fr; }}
      .toolbar {{ justify-content: flex-start; }}
      .meta-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      #workspace {{ order: 1; }}
      .decision {{ order: 2; }}
      .layout > aside.panel:first-child {{ order: 3; }}
      .queue-list {{ max-height: 320px; }}
      .rule-title {{ font-size: 20px; }}
      .choice-row, .actions {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brandline">
        <div class="mark">PG</div>
        <div>
          <h1 data-i18n="appTitle">Pre-Gestor Expert Review</h1>
          <p class="subtitle" data-i18n="subtitle">Validate one fiscal question at a time. Each completed question counts as one review credit.</p>
        </div>
      </div>
      <div class="toolbar">
        <div class="segmented" aria-label="Language">
          <button type="button" data-lang="es">ES</button>
          <button type="button" data-lang="ru">RU</button>
          <button type="button" data-lang="en">EN</button>
        </div>
        <button class="btn subtle" id="exportBtn" type="button" data-i18n="exportJson">Export JSON</button>
        <label class="btn subtle" for="importFile" data-i18n="importJson">Import JSON</label>
        <input id="importFile" type="file" accept="application/json,.json" hidden>
      </div>
    </header>

    <section class="meta-strip" aria-label="Review metrics">
      <div class="metric"><b id="metricTotal">0</b><span data-i18n="metricTotal">Questions</span></div>
      <div class="metric"><b id="metricDone">0</b><span data-i18n="metricDone">Completed</span></div>
      <div class="metric"><b id="metricCredit">€0</b><span data-i18n="metricCredit">Review credit</span></div>
      <div class="metric"><b id="metricQueue">0</b><span data-i18n="metricQueue">Priority queue</span></div>
      <div class="metric"><b id="metricAttention">0</b><span data-i18n="metricAttention">Source attention</span></div>
    </section>

    <div class="layout">
      <aside class="panel">
        <div class="panel-head">
          <div class="panel-title" data-i18n="queueTitle">Audit queue</div>
          <span class="mini" id="queueCount">0</span>
        </div>
        <div class="pad">
          <div class="field">
            <label for="reviewerName" data-i18n="reviewerName">Reviewer</label>
            <input id="reviewerName" autocomplete="name">
          </div>
          <div class="field">
            <label for="reviewerOrg" data-i18n="reviewerOrg">Gestoría / role</label>
            <input id="reviewerOrg">
          </div>
          <div class="field">
            <label for="inviteCode" data-i18n="inviteCode">Invite code</label>
            <input id="inviteCode">
          </div>
          <div class="field">
            <label for="searchBox" data-i18n="search">Search</label>
            <input id="searchBox" placeholder="Modelo 202, Beckham, IVA...">
          </div>
          <div class="field">
            <label for="domainSelect" data-i18n="domain">Domain</label>
            <select id="domainSelect"></select>
          </div>
          <div class="filters" id="filters"></div>
        </div>
        <div class="queue-list" id="queueList"></div>
      </aside>

      <main class="panel" id="workspace">
        <div class="workspace-head">
          <div class="rule-kicker" id="ruleKicker"></div>
          <h2 class="rule-title" id="ruleTitle"></h2>
          <div class="badges" id="badges"></div>
        </div>
        <div class="content-grid">
          <section class="sectionbox">
            <h2 data-i18n="questionToVerify">Question to verify</h2>
            <p id="focusQuestion"></p>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="whyItMatters">Why it matters</h2>
            <p id="practicalText"></p>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="whatToVerify">What to verify</h2>
            <ul class="list" id="verifyList"></ul>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="clientFacts">What to ask or confirm</h2>
            <ul class="list" id="clientList"></ul>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="safeBoundary">Safe Pre-Gestor answer</h2>
            <p id="boundaryText"></p>
          </section>
          <section class="sectionbox">
            <h2 data-i18n="expectedAnswer">Expected reviewer answer</h2>
            <p id="expectedText"></p>
          </section>
          <section class="sectionbox" style="grid-column:1 / -1">
            <h2 data-i18n="sources">Legal basis</h2>
            <p id="sourceIntro" class="source-intro"></p>
            <div class="source-list" id="sourceList"></div>
          </section>
          <section class="sectionbox" style="grid-column:1 / -1">
            <h2 data-i18n="riskFlags">Risk flags</h2>
            <ul class="list" id="riskList"></ul>
          </section>
          <section class="sectionbox technical-box" style="grid-column:1 / -1">
            <details>
              <summary data-i18n="technicalDetails">Technical details</summary>
              <dl class="tech-grid" id="technicalDetails"></dl>
            </details>
          </section>
        </div>
      </main>

      <aside class="panel decision">
        <div class="panel-head">
          <div class="panel-title" data-i18n="decisionTitle">Decision</div>
          <span class="mini" id="positionText"></span>
        </div>
        <div class="pad">
          <div class="progressbar"><div id="progressFill"></div></div>
          <div class="credit">
            <div>
              <div class="choice-label" data-i18n="creditLabel">Current month credit</div>
              <small id="creditDetail"></small>
            </div>
            <b id="creditAmount">€0</b>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="verdict">Verdict</div>
            <div class="choice-row" data-choice-group="verdict"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="sourceSupport">Source support</div>
            <div class="choice-row" data-choice-group="source_support"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="publicSafety">Safe wording</div>
            <div class="choice-row" data-choice-group="public_safety"></div>
          </div>
          <div class="choice-group">
            <div class="choice-label" data-i18n="territoryTime">Territory / period</div>
            <div class="choice-row" data-choice-group="territory_time"></div>
          </div>
          <div class="field">
            <label for="reviewNotes" data-i18n="notes">Notes</label>
            <textarea id="reviewNotes"></textarea>
          </div>
          <div class="field">
            <label for="requiredFix" data-i18n="requiredFix">Required fix</label>
            <textarea id="requiredFix"></textarea>
          </div>
          <div class="actions">
            <button class="btn subtle" id="prevBtn" type="button" data-i18n="previous">Previous</button>
            <button class="btn subtle" id="nextBtn" type="button" data-i18n="next">Next</button>
            <button class="btn primary wide" id="saveNextBtn" type="button" data-i18n="saveNext">Save and next</button>
            <button class="btn subtle wide" id="copyBtn" type="button" data-i18n="copySummary">Copy review summary</button>
          </div>
        </div>
      </aside>
    </div>
  </div>
  <div class="toast" id="toast"></div>
  <script type="application/json" id="dataset-json">{dataset_json}</script>
  <script>
    const DATASET = JSON.parse(document.getElementById("dataset-json").textContent);
    const STORAGE_KEY = "occam.pre_gestor_review_console.v2." + DATASET.dataset_id;
    const CREDIT_PER_QUESTION = DATASET.source.review_unit_credit_eur || 1;
    const I18N = {{
      es: {{
        appTitle: "Revisión experta Pre-Gestor", subtitle: "Valida una pregunta fiscal por vez. Cada pregunta completada cuenta como un crédito de revisión.",
        exportJson: "Exportar JSON", importJson: "Importar JSON", metricTotal: "Preguntas", metricDone: "Completadas", metricCredit: "Crédito", metricQueue: "Prioridad", metricAttention: "Fuentes a revisar",
        queueTitle: "Cola de auditoría", reviewerName: "Revisor", reviewerOrg: "Gestoría / rol", inviteCode: "Código de invitación", search: "Buscar", domain: "Dominio",
        allDomains: "Todos los dominios", all: "Todas", priority: "Prioridad", pending: "Pendientes", completed: "Completadas", sourceAttention: "Fuentes", highStakes: "Alto riesgo",
        questionToVerify: "Tarea de revisión", whyItMatters: "Por qué importa", whatToVerify: "Qué comprobar", clientFacts: "Qué pedir o confirmar", safeBoundary: "Qué puede decir Pre-Gestor", expectedAnswer: "Respuesta esperada del revisor", sources: "Base legal", riskFlags: "Por qué actuar con cautela", technicalDetails: "Detalles técnicos",
        decisionTitle: "Decisión", creditLabel: "Crédito del mes", verdict: "Resultado", sourceSupport: "¿Las fuentes sostienen la conclusión?", publicSafety: "¿La formulación es segura para el cliente?", territoryTime: "¿Territorio y periodo aplican?",
        notes: "Notas", requiredFix: "Corrección obligatoria antes de publicar", previous: "Anterior", next: "Siguiente", saveNext: "Guardar y siguiente", copySummary: "Copiar resumen",
        verified: "Confirmar tal cual", needs_fix: "Confirmar tras corrección", reject: "Rechazar / incorrecto", out_of_scope: "No es mi área", yes: "Sí", partial: "Parcial", no: "No", unclear: "No claro", na: "No aplica",
        saved: "Guardado en este navegador.", exported: "JSON descargado.", imported: "JSON importado.", copied: "Resumen copiado.", noResults: "No hay preguntas con estos filtros.", completeRequired: "Para completar: resultado, fuentes, formulación, territorio/periodo y corrección si hay problema.",
        noFocus: "Revisar hechos, fuentes y condiciones antes de aprobar la tarjeta.", noSources: "No hay fuentes declaradas.", noRisks: "No hay riesgos adicionales declarados.",
        completedDetail: "1 euro por pregunta completada", sourceStatus: "Estado", support: "Soporte", card: "Tarjeta", period: "Periodo", technicalId: "ID técnico", confidence: "Confianza", reviewState: "Estado interno", sourceAttentionBadge: "Revisar fuente", highStakesBadge: "Riesgo alto", priorityBadge: "Prioridad gestor", unreviewedBadge: "Sin revisar"
      }},
      ru: {{
        appTitle: "Экспертная проверка Pre-Gestor", subtitle: "Проверяйте по одному фискальному вопросу. Каждый завершённый вопрос считается как один кредит проверки.",
        exportJson: "Экспорт JSON", importJson: "Импорт JSON", metricTotal: "Вопросы", metricDone: "Завершено", metricCredit: "Кредит", metricQueue: "Приоритет", metricAttention: "Источники",
        queueTitle: "Очередь аудита", reviewerName: "Проверяющий", reviewerOrg: "Организация / роль", inviteCode: "Код приглашения", search: "Поиск", domain: "Область",
        allDomains: "Все области", all: "Все", priority: "Приоритет", pending: "Незавершённые", completed: "Завершено", sourceAttention: "Источники", highStakes: "Высокий риск",
        questionToVerify: "Задача проверки", whyItMatters: "Зачем это важно", whatToVerify: "Что сверить", clientFacts: "Что запросить или подтвердить", safeBoundary: "Что может безопасно сказать Pre-Gestor", expectedAnswer: "Какой ответ ждём от проверяющего", sources: "Правовое основание", riskFlags: "Почему нужна осторожность", technicalDetails: "Технические детали",
        decisionTitle: "Решение", creditLabel: "Кредит текущего месяца", verdict: "Итог", sourceSupport: "Источники действительно подтверждают вывод?", publicSafety: "Формулировка безопасна для клиента?", territoryTime: "Территория и период применимы?",
        notes: "Заметки", requiredFix: "Обязательная правка перед публикацией", previous: "Назад", next: "Дальше", saveNext: "Сохранить и дальше", copySummary: "Скопировать резюме",
        verified: "Подтвердить как есть", needs_fix: "Подтвердить после правки", reject: "Отклонить / неверно", out_of_scope: "Не моя область", yes: "Да", partial: "Частично", no: "Нет", unclear: "Неясно", na: "Не применимо",
        saved: "Сохранено в этом браузере.", exported: "JSON скачан.", imported: "JSON импортирован.", copied: "Резюме скопировано.", noResults: "Нет вопросов с такими фильтрами.", completeRequired: "Для завершения нужны итог, источники, формулировка, территория/период и правка, если есть проблема.",
        noFocus: "Сверить факты, источники и условия перед одобрением карточки.", noSources: "Источники не указаны.", noRisks: "Дополнительные риски не указаны.",
        completedDetail: "1 евро за завершённый вопрос", sourceStatus: "Статус", support: "Поддержка", card: "Карточка", period: "Период", technicalId: "Технический ID", confidence: "Уверенность", reviewState: "Внутренний статус", sourceAttentionBadge: "Проверить источник", highStakesBadge: "Высокий риск", priorityBadge: "Приоритет гестора", unreviewedBadge: "Не проверено"
      }},
      en: {{
        appTitle: "Pre-Gestor Expert Review", subtitle: "Validate one fiscal question at a time. Each completed question counts as one review credit.",
        exportJson: "Export JSON", importJson: "Import JSON", metricTotal: "Questions", metricDone: "Completed", metricCredit: "Credit", metricQueue: "Priority queue", metricAttention: "Source attention",
        queueTitle: "Audit queue", reviewerName: "Reviewer", reviewerOrg: "Gestoría / role", inviteCode: "Invite code", search: "Search", domain: "Domain",
        allDomains: "All domains", all: "All", priority: "Priority", pending: "Pending", completed: "Completed", sourceAttention: "Sources", highStakes: "High stakes",
        questionToVerify: "Review task", whyItMatters: "Why it matters", whatToVerify: "What to verify", clientFacts: "What to ask or confirm", safeBoundary: "What Pre-Gestor may safely say", expectedAnswer: "Expected reviewer answer", sources: "Legal basis", riskFlags: "Why caution is needed", technicalDetails: "Technical details",
        decisionTitle: "Decision", creditLabel: "Current month credit", verdict: "Outcome", sourceSupport: "Do the sources support the conclusion?", publicSafety: "Is the wording safe for the client?", territoryTime: "Do territory and period apply?",
        notes: "Notes", requiredFix: "Required fix before publication", previous: "Previous", next: "Next", saveNext: "Save and next", copySummary: "Copy review summary",
        verified: "Confirm as-is", needs_fix: "Confirm after fix", reject: "Reject / incorrect", out_of_scope: "Not my area", yes: "Yes", partial: "Partial", no: "No", unclear: "Unclear", na: "N/A",
        saved: "Saved in this browser.", exported: "JSON downloaded.", imported: "JSON imported.", copied: "Summary copied.", noResults: "No questions match these filters.", completeRequired: "To complete: outcome, sources, wording, territory/period and required fix when there is a problem.",
        noFocus: "Review facts, sources and conditions before approving the card.", noSources: "No sources declared.", noRisks: "No additional risks declared.",
        completedDetail: "1 euro per completed question", sourceStatus: "Status", support: "Support", card: "Card", period: "Period", technicalId: "Technical ID", confidence: "Confidence", reviewState: "Internal status", sourceAttentionBadge: "Review source", highStakesBadge: "High risk", priorityBadge: "Gestor priority", unreviewedBadge: "Unreviewed"
      }}
    }};
    const CHOICES = {{
      verdict: ["verified", "needs_fix", "reject", "out_of_scope"],
      source_support: ["yes", "partial", "no", "unclear"],
      public_safety: ["yes", "partial", "no"],
      territory_time: ["yes", "partial", "no", "na"]
    }};
    const state = loadState();
    let lang = state.lang || "es";
    let filter = state.filter || "all";
    let domain = state.domain || "all";
    let current = Number.isInteger(state.current) ? state.current : 0;

    function blankReview() {{
      return {{ verdict: "", source_support: "", public_safety: "", territory_time: "", notes: "", required_fix: "", reviewed_at: "" }};
    }}
    function loadState() {{
      try {{ return {{ reviewer: {{}}, reviews: {{}}, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}") }}; }}
      catch {{ return {{ reviewer: {{}}, reviews: {{}} }}; }}
    }}
    function t(key) {{ return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key; }}
    function domainLabel(rule) {{ return (rule.domain_labels && (rule.domain_labels[lang] || rule.domain_labels.en)) || rule.domain_label || rule.domain_id; }}
    function brief(rule) {{ return (rule.briefs && (rule.briefs[lang] || rule.briefs.en)) || {{ short_title: rule.rule_id, question: t("noFocus"), why: "", law: "", verify: [], request: [], boundary: "", expected: "" }}; }}
    function review(rule) {{
      state.reviews[rule.rule_id] ||= blankReview();
      return state.reviews[rule.rule_id];
    }}
    function needsFixText(r) {{
      return ["needs_fix", "reject"].includes(r.verdict)
        || ["partial", "no", "unclear"].includes(r.source_support)
        || ["partial", "no"].includes(r.public_safety)
        || ["partial", "no"].includes(r.territory_time);
    }}
    function isDone(rule) {{
      const r = review(rule);
      const axes = Boolean(r.verdict && r.source_support && r.public_safety && r.territory_time);
      return axes && (!needsFixText(r) || Boolean((r.required_fix || "").trim()));
    }}
    function save(showToast = false) {{
      const rule = visibleRules()[current] || DATASET.rules[0];
      if (rule) {{
        const r = review(rule);
        r.notes = document.getElementById("reviewNotes").value.trim();
        r.required_fix = document.getElementById("requiredFix").value.trim();
        if (r.verdict && !r.reviewed_at) r.reviewed_at = new Date().toISOString();
      }}
      state.reviewer = {{
        name: document.getElementById("reviewerName").value.trim(),
        organization: document.getElementById("reviewerOrg").value.trim(),
        invite_code: document.getElementById("inviteCode").value.trim()
      }};
      state.lang = lang; state.filter = filter; state.domain = domain; state.current = current;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      if (showToast) toast(t("saved"));
      renderMetrics(); renderQueue();
    }}
    function visibleRules() {{
      const q = document.getElementById("searchBox").value.trim().toLowerCase();
      return DATASET.rules.filter(rule => {{
        const r = review(rule);
        const b = brief(rule);
        const text = [
          rule.rule_id, domainLabel(rule), rule.scenario,
          b.short_title, b.question, b.why, b.law,
          rule.texts.en.summary, rule.texts.es.summary, rule.texts.ru.summary
        ].join(" ").toLowerCase();
        if (q && !text.includes(q)) return false;
        if (domain !== "all" && rule.domain_id !== domain) return false;
        if (filter === "priority" && !rule.tags.includes("gestor_queue")) return false;
        if (filter === "pending" && isDone(rule)) return false;
        if (filter === "completed" && !isDone(rule)) return false;
        if (filter === "sourceAttention" && !rule.tags.includes("source_attention")) return false;
        if (filter === "highStakes" && !rule.high_stakes) return false;
        return true;
      }});
    }}
    function setLang(next) {{
      lang = next;
      document.documentElement.lang = lang;
      document.querySelectorAll("[data-lang]").forEach(btn => btn.classList.toggle("active", btn.dataset.lang === lang));
      document.querySelectorAll("[data-i18n]").forEach(node => node.textContent = t(node.dataset.i18n));
      renderDomains(); renderFilters(); renderChoices(); renderRule(); renderMetrics(); save(false);
    }}
    function renderDomains() {{
      const selected = domain;
      const domains = [...new Map(DATASET.rules.map(rule => [rule.domain_id, domainLabel(rule)])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
      document.getElementById("domainSelect").innerHTML = [`<option value="all">${{escapeHtml(t("allDomains"))}}</option>`]
        .concat(domains.map(([id, label]) => `<option value="${{escapeAttr(id)}}">${{escapeHtml(label)}}</option>`)).join("");
      document.getElementById("domainSelect").value = selected;
    }}
    function renderFilters() {{
      const filters = ["all", "priority", "pending", "completed", "sourceAttention", "highStakes"];
      document.getElementById("filters").innerHTML = filters.map(name => `<button class="chip ${{filter === name ? "active" : ""}}" data-filter="${{name}}" type="button">${{escapeHtml(t(name))}}</button>`).join("");
      document.querySelectorAll("[data-filter]").forEach(btn => btn.onclick = () => {{ filter = btn.dataset.filter; current = 0; renderFilters(); renderQueue(); renderRule(); save(false); }});
    }}
    function renderChoices() {{
      Object.entries(CHOICES).forEach(([group, values]) => {{
        const node = document.querySelector(`[data-choice-group="${{group}}"]`);
        node.innerHTML = values.map(value => `<button type="button" class="choice ${{value}}" data-choice-group-name="${{group}}" data-choice-value="${{value}}">${{escapeHtml(t(value))}}</button>`).join("");
      }});
    }}
    function renderQueue() {{
      const visible = visibleRules();
      document.getElementById("queueCount").textContent = String(visible.length);
      if (current >= visible.length) current = Math.max(0, visible.length - 1);
      const list = document.getElementById("queueList");
      if (!visible.length) {{
        list.innerHTML = `<div class="empty">${{escapeHtml(t("noResults"))}}</div>`;
        return;
      }}
      list.innerHTML = visible.map((rule, index) => {{
        const r = review(rule);
        const b = brief(rule);
        const title = b.short_title || rule.texts[lang]?.title || rule.texts.en.title || rule.rule_id;
        const sub = `${{domainLabel(rule)}} · ${{t("card")}} ${{rule.index}}`;
        return `<button class="queue-row ${{index === current ? "active" : ""}}" type="button" data-row="${{index}}">
          <span class="index-dot">${{rule.index}}</span>
          <span><strong>${{escapeHtml(title)}}</strong><small>${{escapeHtml(sub)}}</small></span>
          <span class="status-dot ${{escapeAttr(r.verdict)}}"></span>
        </button>`;
      }}).join("");
      document.querySelectorAll("[data-row]").forEach(btn => btn.onclick = () => {{ save(false); current = Number(btn.dataset.row); renderRule(); renderQueue(); }});
    }}
    function renderRule() {{
      const visible = visibleRules();
      if (!visible.length) return;
      if (current >= visible.length) current = Math.max(0, visible.length - 1);
      const rule = visible[current];
      const r = review(rule);
      const b = brief(rule);
      document.getElementById("positionText").textContent = `${{current + 1}} / ${{visible.length}}`;
      document.getElementById("ruleKicker").textContent = `${{t("card")}} ${{rule.index}} · ${{domainLabel(rule)}}`;
      document.getElementById("ruleTitle").textContent = b.short_title || rule.rule_id;
      document.getElementById("focusQuestion").textContent = b.question || t("noFocus");
      document.getElementById("practicalText").textContent = b.why || "";
      document.getElementById("badges").innerHTML = badges(rule, r).map(item => `<span class="badge ${{item.cls}}">${{escapeHtml(item.text)}}</span>`).join("");
      renderList("verifyList", b.verify || []);
      renderList("clientList", b.request || []);
      document.getElementById("boundaryText").textContent = b.boundary || "";
      document.getElementById("expectedText").textContent = b.expected || "";
      document.getElementById("sourceIntro").textContent = b.source_intro || b.law || "";
      renderSources(rule);
      renderRisks(rule);
      renderTechnical(rule);
      Object.entries(CHOICES).forEach(([group]) => {{
        document.querySelectorAll(`[data-choice-group-name="${{group}}"]`).forEach(btn => btn.classList.toggle("selected", btn.dataset.choiceValue === r[group]));
      }});
      document.getElementById("reviewNotes").value = r.notes || "";
      document.getElementById("requiredFix").value = r.required_fix || "";
      document.getElementById("prevBtn").disabled = current <= 0;
      document.getElementById("nextBtn").disabled = current >= visible.length - 1;
    }}
    function badges(rule, r) {{
      const items = [
        {{ text: t("unreviewedBadge"), cls: "ok" }},
        {{ text: rule.valid_from ? `${{t("period")}} ${{rule.valid_from}}${{rule.valid_until ? " → " + rule.valid_until : ""}}` : "", cls: "" }}
      ];
      if (rule.tags.includes("gestor_queue")) items.push({{ text: t("priorityBadge"), cls: "queue" }});
      if (rule.high_stakes) items.push({{ text: t("highStakesBadge"), cls: "high" }});
      if (rule.tags.includes("source_attention")) items.push({{ text: t("sourceAttentionBadge"), cls: "source" }});
      if (r.verdict) items.push({{ text: t(r.verdict), cls: "ok" }});
      return items.filter(item => item.text);
    }}
    function renderList(id, items) {{
      document.getElementById(id).innerHTML = (items && items.length)
        ? items.map(item => `<li>${{escapeHtml(item)}}</li>`).join("")
        : `<li>${{escapeHtml(t("noFocus"))}}</li>`;
    }}
    function renderSources(rule) {{
      const node = document.getElementById("sourceList");
      if (!rule.sources.length) {{
        node.innerHTML = `<div class="source"><small>${{escapeHtml(t("noSources"))}}</small></div>`;
        return;
      }}
      node.innerHTML = rule.sources.map(source => {{
        const pub = source.public?.[lang] || source.public?.en || {{}};
        const status = [pub.meta].filter(Boolean).join(" · ");
        const stateClass = source.support_state === "yes" ? "ok" : "source";
        const title = pub.title || source.support_anchor || source.title || t("noSources");
        const titleHtml = source.url
          ? `<a href="${{escapeAttr(source.url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(title)}}</a>`
          : `<strong>${{escapeHtml(title)}}</strong>`;
        return `<article class="source">
          <div class="source-top">
            <div>${{titleHtml}}<small>${{escapeHtml(status)}}</small></div>
            <span class="badge ${{stateClass}}">${{escapeHtml(pub.support || t("support"))}}</span>
          </div>
          <div class="claim-text">${{escapeHtml(pub.note || "")}}</div>
        </article>`;
      }}).join("");
    }}
    function renderRisks(rule) {{
      const risks = rule.risk_flags || [];
      document.getElementById("riskList").innerHTML = risks.length
        ? risks.map(risk => `<li>${{riskText(risk)}}</li>`).join("")
        : `<li>${{escapeHtml(t("noRisks"))}}</li>`;
    }}
    function riskText(risk) {{
      if (risk.public && (risk.public[lang] || risk.public.en)) return escapeHtml(risk.public[lang] || risk.public.en);
      const code = String(risk.code || "").replace(/_/g, " ");
      const severity = String(risk.severity || "").replace(/_/g, " ");
      if (lang === "ru") return escapeHtml(`Проверить осторожно: ${{code}}${{severity ? " (" + severity + ")" : ""}}.`);
      if (lang === "es") return escapeHtml(`Revisar con cautela: ${{code}}${{severity ? " (" + severity + ")" : ""}}.`);
      return escapeHtml(`Review with caution: ${{code}}${{severity ? " (" + severity + ")" : ""}}.`);
    }}
    function renderTechnical(rule) {{
      const rows = [
        [t("technicalId"), rule.rule_id],
        [t("reviewState"), rule.gestor_review_state],
        [t("confidence"), rule.confidence],
        ["Commit", DATASET.source.commit],
        ["Pack", rule.pack_file],
        ["Scenario", rule.scenario],
        ["Source IDs", (rule.sources || []).map(source => source.source_id).join(", ")]
      ];
      document.getElementById("technicalDetails").innerHTML = rows
        .filter(([, value]) => value !== undefined && value !== null && String(value).trim())
        .map(([key, value]) => `<dt>${{escapeHtml(key)}}</dt><dd>${{escapeHtml(value)}}</dd>`)
        .join("");
    }}
    function renderMetrics() {{
      const done = DATASET.rules.filter(isDone).length;
      const credit = done * CREDIT_PER_QUESTION;
      const pct = DATASET.rules.length ? Math.round(done / DATASET.rules.length * 100) : 0;
      document.getElementById("metricTotal").textContent = DATASET.rules.length;
      document.getElementById("metricDone").textContent = done;
      document.getElementById("metricCredit").textContent = `€${{credit}}`;
      document.getElementById("metricQueue").textContent = DATASET.stats.gestor_queue;
      document.getElementById("metricAttention").textContent = DATASET.stats.source_attention;
      document.getElementById("creditAmount").textContent = `€${{credit}}`;
      document.getElementById("creditDetail").textContent = `${{done}}/${{DATASET.rules.length}} · ${{t("completedDetail")}}`;
      document.getElementById("progressFill").style.width = pct + "%";
    }}
    function exportJson() {{
      save(false);
      const reviews = DATASET.rules
        .map(rule => ({{ rule_id: rule.rule_id, ...review(rule) }}))
        .filter(item => ["verdict", "source_support", "public_safety", "territory_time", "notes", "required_fix"].some(key => Boolean(item[key])));
      const payload = {{
        schema: "pre_gestor_expert_review_submission.v2",
        exported_at: new Date().toISOString(),
        dataset_id: DATASET.dataset_id,
        dataset_commit: DATASET.source.commit,
        reviewer: state.reviewer,
        credit_eur: DATASET.rules.filter(isDone).length * CREDIT_PER_QUESTION,
        completed_count: DATASET.rules.filter(isDone).length,
        reviews
      }};
      const name = (state.reviewer.name || "reviewer").toLowerCase().replace(/[^a-z0-9а-яё_-]+/giu, "_").slice(0, 40) || "reviewer";
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pre-gestor-review-${{name}}-${{new Date().toISOString().slice(0, 10)}}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 500);
      toast(t("exported"));
    }}
    function importJson(file) {{
      const reader = new FileReader();
      reader.onload = () => {{
        const payload = JSON.parse(String(reader.result || "{{}}"));
        if (payload.reviewer) state.reviewer = payload.reviewer;
        (payload.reviews || []).forEach(item => {{
          if (!item.rule_id) return;
          const {{ rule_id, ...body }} = item;
          state.reviews[rule_id] = {{ ...blankReview(), ...body }};
        }});
        hydrateReviewer(); save(false); renderAll(); toast(t("imported"));
      }};
      reader.readAsText(file);
    }}
    async function copySummary() {{
      save(false);
      const rule = visibleRules()[current] || DATASET.rules[0];
      const r = review(rule);
      const text = [
        `Dataset: ${{DATASET.dataset_id}} @ ${{DATASET.source.commit}}`,
        `Rule: ${{rule.rule_id}}`,
        `Reviewer: ${{state.reviewer.name || ""}}`,
        `Verdict: ${{r.verdict || ""}}`,
        `Source support: ${{r.source_support || ""}}`,
        `Notes: ${{r.notes || ""}}`,
        `Required fix: ${{r.required_fix || ""}}`
      ].join("\\n");
      await navigator.clipboard.writeText(text);
      toast(t("copied"));
    }}
    function hydrateReviewer() {{
      document.getElementById("reviewerName").value = state.reviewer.name || "";
      document.getElementById("reviewerOrg").value = state.reviewer.organization || "";
      document.getElementById("inviteCode").value = state.reviewer.invite_code || "";
    }}
    function toast(message) {{
      const node = document.getElementById("toast");
      node.textContent = message;
      node.classList.add("show");
      clearTimeout(toast.timer);
      toast.timer = setTimeout(() => node.classList.remove("show"), 1800);
    }}
    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, ch => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[ch]));
    }}
    function escapeAttr(value) {{ return escapeHtml(value).replace(/`/g, "&#96;"); }}
    function renderAll() {{ renderDomains(); renderFilters(); renderChoices(); renderQueue(); renderRule(); renderMetrics(); }}

    document.querySelectorAll("[data-lang]").forEach(btn => btn.onclick = () => setLang(btn.dataset.lang));
    document.getElementById("domainSelect").onchange = event => {{ domain = event.target.value; current = 0; renderQueue(); renderRule(); save(false); }};
    document.getElementById("searchBox").oninput = () => {{ current = 0; renderQueue(); renderRule(); save(false); }};
    ["reviewerName", "reviewerOrg", "inviteCode", "reviewNotes", "requiredFix"].forEach(id => document.getElementById(id).addEventListener("input", () => save(false)));
    document.addEventListener("click", event => {{
      const btn = event.target.closest("[data-choice-group-name]");
      if (!btn) return;
      const rule = visibleRules()[current] || DATASET.rules[0];
      const r = review(rule);
      r[btn.dataset.choiceGroupName] = btn.dataset.choiceValue;
      if (btn.dataset.choiceGroupName === "verdict") r.reviewed_at = new Date().toISOString();
      save(false); renderRule(); renderMetrics();
    }});
    document.getElementById("prevBtn").onclick = () => {{ save(false); current = Math.max(0, current - 1); renderRule(); renderQueue(); }};
    document.getElementById("nextBtn").onclick = () => {{ save(false); current = Math.min(visibleRules().length - 1, current + 1); renderRule(); renderQueue(); }};
    document.getElementById("saveNextBtn").onclick = () => {{
      const rule = visibleRules()[current] || DATASET.rules[0];
      save(false);
      if (!isDone(rule)) {{
        toast(t("completeRequired"));
        renderRule(); renderQueue(); renderMetrics();
        return;
      }}
      toast(t("saved"));
      current = Math.min(visibleRules().length - 1, current + 1);
      renderRule(); renderQueue();
    }};
    document.getElementById("exportBtn").onclick = exportJson;
    document.getElementById("copyBtn").onclick = copySummary;
    document.getElementById("importFile").onchange = event => event.target.files?.[0] && importJson(event.target.files[0]);

    hydrateReviewer();
    setLang(lang);
  </script>
  <!-- Generated: {html.escape(generated_at)} -->
</body>
</html>
"""


def build(data_dir: Path, out_path: Path, source_label: str, source_commit: str) -> None:
    dataset = _build_dataset(data_dir, source_label, source_commit)
    generated_at = dataset["generated_at"]
    dataset_json = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = _page_template(dataset_json, generated_at)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path, help="Path to pre_gestor_intelligence/data")
    parser.add_argument("--out", default=Path("pre-gestor-a1-review/index.html"), type=Path)
    parser.add_argument("--source-label", default="codex/pre-gestor-core")
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    source_commit = args.source_commit or _git_commit(data_dir.parents[2])
    build(data_dir, args.out.expanduser().resolve(), args.source_label, source_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
