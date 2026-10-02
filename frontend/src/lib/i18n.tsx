"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/**
 * Multilingual foundation. English is the default and the source of truth; Hindi and Telugu cover the
 * navigation shell. Strings missing from a dictionary fall back to English, so nothing ever renders blank.
 * Translations are a prototype set pending review by native-speaker editors. Scientific content is NOT
 * machine-translated here — content translation goes through the reviewed Content Studio workflow.
 */
export type Lang = "en" | "hi" | "te";
export const LANGS: { code: Lang; label: string; native: string }[] = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
];

const HI: Record<string, string> = {
  Discover: "खोज", Intelligence: "बुद्धिमत्ता", Outreach: "आउटरीच", Management: "प्रबंधन",
  Home: "होम", Explore: "खोजें", Documents: "दस्तावेज़", Datasets: "डेटासेट", Media: "मीडिया", Expeditions: "अभियान",
  "Research Stations": "अनुसंधान केंद्र", "Institutional Activities": "संस्थागत गतिविधियाँ", "Polar Map": "ध्रुवीय मानचित्र",
  "Learn Polar Science": "ध्रुवीय विज्ञान सीखें", "AI Assistant": "एआई सहायक", "Smart Search": "स्मार्ट खोज",
  "Knowledge Timeline": "ज्ञान समयरेखा", "Impact & KPIs": "प्रभाव और KPI", "Outreach Feed": "आउटरीच फ़ीड",
  "Content Studio": "सामग्री स्टूडियो", "Review Center": "समीक्षा केंद्र", "Researcher Workspace": "शोधकर्ता कार्यक्षेत्र",
  "My Knowledge": "मेरा ज्ञान", Dashboard: "डैशबोर्ड", Repository: "भंडार", "Provenance & Verification": "उत्पत्ति और सत्यापन",
  "Manage Activities": "गतिविधियाँ प्रबंधित करें", "Users & Roles": "उपयोगकर्ता और भूमिकाएँ", Analytics: "विश्लेषण",
  "Audit Logs": "ऑडिट लॉग", "System Health": "सिस्टम स्थिति", "Search polar knowledge…": "ध्रुवीय ज्ञान खोजें…",
  "Ask AI": "एआई से पूछें", "Sign in": "साइन इन करें", Map: "मानचित्र", Menu: "मेनू",
  "Demo corpus — not official institutional data.": "डेमो संग्रह — आधिकारिक संस्थागत डेटा नहीं।",
  "Language": "भाषा", "Prototype translation": "प्रोटोटाइप अनुवाद",
  "Research Stories": "शोध कहानियाँ", "Visual Media Search": "दृश्य मीडिया खोज", "Campaign Planner": "अभियान योजनाकार",
  "Content Calendar": "सामग्री कैलेंडर", "Outreach Analytics": "आउटरीच विश्लेषण",
};
const TE: Record<string, string> = {
  Discover: "కనుగొనండి", Intelligence: "మేధస్సు", Outreach: "ఔట్‌రీచ్", Management: "నిర్వహణ",
  Home: "హోమ్", Explore: "అన్వేషించండి", Documents: "పత్రాలు", Datasets: "డేటాసెట్‌లు", Media: "మీడియా", Expeditions: "యాత్రలు",
  "Research Stations": "పరిశోధన కేంద్రాలు", "Institutional Activities": "సంస్థాగత కార్యకలాపాలు", "Polar Map": "ధ్రువ పటం",
  "Learn Polar Science": "ధ్రువ శాస్త్రం నేర్చుకోండి", "AI Assistant": "AI సహాయకుడు", "Smart Search": "స్మార్ట్ శోధన",
  "Knowledge Timeline": "జ్ఞాన కాలక్రమం", "Impact & KPIs": "ప్రభావం & KPIలు", "Outreach Feed": "ఔట్‌రీచ్ ఫీడ్",
  "Content Studio": "కంటెంట్ స్టూడియో", "Review Center": "సమీక్ష కేంద్రం", "Researcher Workspace": "పరిశోధకుల కార్యస్థలం",
  "My Knowledge": "నా జ్ఞానం", Dashboard: "డాష్‌బోర్డ్", Repository: "రిపోజిటరీ", "Provenance & Verification": "మూలం & ధృవీకరణ",
  "Manage Activities": "కార్యకలాపాల నిర్వహణ", "Users & Roles": "వినియోగదారులు & పాత్రలు", Analytics: "విశ్లేషణలు",
  "Audit Logs": "ఆడిట్ లాగ్‌లు", "System Health": "సిస్టమ్ స్థితి", "Search polar knowledge…": "ధ్రువ జ్ఞానాన్ని శోధించండి…",
  "Ask AI": "AIని అడగండి", "Sign in": "సైన్ ఇన్", Map: "పటం", Menu: "మెను",
  "Demo corpus — not official institutional data.": "డెమో సేకరణ — అధికారిక సంస్థాగత డేటా కాదు.",
  "Language": "భాష", "Prototype translation": "ప్రోటోటైప్ అనువాదం",
  "Research Stories": "పరిశోధన కథనాలు", "Visual Media Search": "దృశ్య మీడియా శోధన", "Campaign Planner": "ప్రచార ప్రణాళిక",
  "Content Calendar": "కంటెంట్ క్యాలెండర్", "Outreach Analytics": "ఔట్‌రీచ్ విశ్లేషణలు",
};
const DICTS: Record<Lang, Record<string, string>> = { en: {}, hi: HI, te: TE };
const KEY = "polarnexus.lang";

interface I18n { lang: Lang; setLang: (l: Lang) => void; t: (s: string) => string }
const Ctx = createContext<I18n>({ lang: "en", setLang: () => {}, t: (s) => s });

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    try {
      const v = window.localStorage.getItem(KEY) as Lang | null;
      if (v && v in DICTS) setLangState(v);
    } catch {
      /* storage unavailable — English */
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      window.localStorage.setItem(KEY, l);
    } catch {
      /* ignore */
    }
  }, []);
  const t = useCallback((s: string) => DICTS[lang][s] || s, [lang]);
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
