import streamlit as st
import pandas as pd
from weasyprint import HTML
import io
import zipfile
import re

# Słownik do konwersji nazw miesięcy (skróty i pełne) na numery MM
MONTHS_MAP = {
    'jan': '01', 'january': '01',
    'feb': '02', 'february': '02',
    'mar': '03', 'march': '03',
    'apr': '04', 'april': '04',
    'may': '05',
    'jun': '06', 'june': '06',
    'jul': '07', 'july': '07',
    'aug': '08', 'august': '08',
    'sep': '09', 'september': '09',
    'oct': '10', 'october': '10',
    'nov': '11', 'november': '11',
    'dec': '12', 'december': '12'
}

# Słownik z polskimi miesiącami w dopełniaczu (do treści dokumentu)
MONTHS_PL_GENITIVE = {
    'jan': 'stycznia', 'feb': 'lutego', 'mar': 'marca', 'apr': 'kwietnia',
    'may': 'maja', 'jun': 'czerwca', 'jul': 'lipca', 'aug': 'sierpnia',
    'sep': 'września', 'oct': 'października', 'nov': 'listopada', 'dec': 'grudnia'
}

# Słownik tłumaczeń rodzajów nieobecności z angielskiego na polski
POLICY_TRANSLATIONS = {
    'holidays': 'Urlop wypoczynkowy',
    'vacation': 'Urlop wypoczynkowy',
    'annual leave': 'Urlop wypoczynkowy',
    'maternity leave': 'Urlop macierzyński',
    'paternity leave': 'Urlop ojcostwa',
    'parental leave': 'Urlop rodzicielski',
    'sick leave': 'Zwolnienie lekarskie',
    'unpaid leave': 'Urlop bezpłatny',
    'home office': 'Praca zdalna',
    'remote work': 'Praca zdalna',
    'remote': 'Praca zdalna',
    'workation': 'Workation (Praca zdalna)',
    'personal leave': 'Urlop okolicznościowy',
    'compassionate leave': 'Urlop okolicznościowy',
    'child care': 'Opieka nad dzieckiem',
    'care leave': 'Urlop opiekuńczy',
    'force majeure': 'Zwolnienie od pracy z powodu siły wyższej'
}

def translate_policy(policy_str):
    """Przekształca angielską nazwę polityki na poprawną polską."""
    if not isinstance(policy_str, str) or not policy_str.strip():
        return "Urlop wypoczynkowy"
    
    clean_policy = policy_str.strip().lower()
    return POLICY_TRANSLATIONS.get(clean_policy, policy_str.strip())

def clean_date_part(date_str, default_year=None):
    """Pomocnicza funkcja czyszcząca i tłumacząca pojedynczy fragment daty z twardymi spacjami."""
    date_str = date_str.replace('(All day)', '').replace(',', '').strip()
    parts = date_str.split()
    
    if len(parts) == 3:  # np. ['28', 'Sep', '2026']
        day, month, year = parts
    elif len(parts) == 2:  # np. ['28', 'Sep']
        day, month = parts
        year = default_year
    else:
        return date_str

    day = day.zfill(2)
    month_pl = MONTHS_PL_GENITIVE.get(month.lower()[:3], month)
    
    if year:
        return f"{day}\u00A0{month_pl}\u00A0{year}\u00A0r."
    return f"{day}\u00A0{month_pl}"

def parse_english_period_to_pl(period_str):
    """Główna funkcja parsująca zakresy i pojedyncze daty nieobecności."""
    if not isinstance(period_str, str) or not period_str.strip():
        return period_str

    clean_str = re.sub(r'\s*\([^)]*\)', '', period_str).strip()

    if '-' in clean_str:
        parts = clean_str.split('-')
        start_part = parts[0].strip()
        end_part = parts[1].strip()

        year_match = re.search(r'\b(20\d{2})\b', end_part)
        fallback_year = year_match.group(1) if year_match else None

        start_year_match = re.search(r'\b(20\d{2})\b', start_part)
        start_year = start_year_match.group(1) if start_year_match else fallback_year

        start_pl = clean_date_part(start_part, default_year=start_year)
        end_pl = clean_date_part(end_part, default_year=fallback_year)

        return f"{start_pl}\u00A0–\u00A0{end_pl}"
    else:
        return clean_date_part(clean_str)

def convert_single_date_to_pl(date_str):
    """Konwersja daty utworzenia wniosku."""
    if not isinstance(date_str, str):
        return date_str
    clean_str = date_str.replace(',', '').strip()
    parts = clean_str.split()
    if len(parts) == 3:
        day, month, year = parts
        month_pl = MONTHS_PL_GENITIVE.get(month.lower()[:3], month)
        return f"{day.zfill(2)}\u00A0{month_pl}\u00A0{year}"
    return date_str

def sanitize_filename(text):
    """Usuwa niedozwolone znaki z nazw plików."""
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    return text.replace(' ', '_').strip()

def extract_numeric_date_for_filename(period_str):
    """Przekształca angielską datę (np. 28 Sep 2026) na cyfrowy format YYYY-MM-DD."""
    if not isinstance(period_str, str):
        return "brak-daty"
    
    clean_str = period_str.replace('(All day)', '').replace(',', '').strip()
    first_date = clean_str.split('-')[0].strip()
    parts = first_date.split()
    
    if len(parts) >= 2:
        day = parts[0].zfill(2)
        month_str = parts[1].lower()[:3]
        month_num = MONTHS_MAP.get(month_str, "01")
        year = parts[2] if len(parts) == 3 else "2026"
        return f"{year}-{month_num}-{day}"
    
    return sanitize_filename(first_date)

def get_company_header(company_type):
    """Zwraca nagłówek HTML dla wybranej spółki."""
    if company_type == "SRI":
        return """
            <strong>SCIENTIA RESEARCH INSTITUTE Sp. z o.o.</strong><br>
            ul. Michała Kleofasa Ogińskiego 2, 85-092 Bydgoszcz<br>
            NIP: 9532779052 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; REGON: 387251647 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KRS: 0000864098
        """
    else:  # Domyślnie CRO
        return """
            <strong>SCIENTIA CRO Sp. z o.o.</strong><br>
            ul. Ogińskiego 2, 85-092 Bydgoszcz<br>
            KRS 0000999674 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; NIP 9671460288 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; REGON 523240305
        """

st.set_page_config(
    page_title="Generator Wniosków - SCIENTIA",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Generator Wniosków Urlopowych i Pracy Zdalnej - SCIENTIA")
st.markdown("Wgraj pliki raportu oraz przypisania spółek, aby wygenerować spersonalizowane PDF-y.")

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("1. Wgraj raport nieobecności (.xlsx lub .csv)", type=["xlsx", "csv"])

with col2:
    company_mapping_file = st.file_uploader("2. [Opcjonalnie] Wgraj listę przynależności do spółek (.xlsx)", type=["xlsx"])

city_input = st.text_input("Miejscowość wystawienia wniosku:", value="Bydgoszcz")

company_map = {}
if company_mapping_file is not None:
    try:
        mapping_df = pd.read_excel(company_mapping_file)
        req_col = [c for c in mapping_df.columns if 'pracownik' in c.lower() or 'person' in c.lower() or 'requester' in c.lower() or 'imię' in c.lower()]
        comp_col = [c for c in mapping_df.columns if 'spółka' in c.lower() or 'spolka' in c.lower() or 'company' in c.lower()]
        
        if req_col and comp_col:
            for _, r in mapping_df.iterrows():
                person = str(r[req_col[0]]).strip().lower()
                comp = str(r[comp_col[0]]).strip()
                company_map[person] = "SRI" if ("institute" in comp.lower() or "sri" in comp.lower() or "research" in comp.lower()) else "CRO"
            st.info("Załadowano przypisania do spółek z pliku.")
        else:
            st.warning("Plik spółek wgrany, ale nie odnaleziono kolumn z pracownikiem/spółką. Domyślnie wygenerowane zostaną wnioski CRO.")
    except Exception as e:
        st.error(f"Błąd odczytu pliku spółek: {e}")

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.columns = df.columns.str.strip()

        def is_approved(row):
            status = str(row.get('Status', '')).strip().upper()
            approved_by = str(row.get('Approved by', '')).strip()

            if status in ['APPROVED', 'APPROVE_NOT_REQUIRED']:
                return True
            if status == 'PENDING' and approved_by.lower() != 'automatically' and approved_by != '':
                return True
            return False

        df['IsApproved'] = df.apply(is_approved, axis=1)
        approved_df = df[df['IsApproved'] == True].copy().reset_index(drop=True)

        if not approved_df.empty:
            st.success(f"Znaleziono **{len(approved_df)}** zaakceptowanych / zatwierdzonych wniosków.")

            st.subheader("📋 Wybierz rekordy do wygenerowania:")
            
            approved_df.insert(0, "Wybierz", True)
            
            display_cols = ['Wybierz', 'Date created', 'Requester', 'Policy', 'Time off period', 'Status', 'Approved by', 'Notes']
            available_cols = [col for col in display_cols if col in approved_df.columns]

            edited_df = st.data_editor(
                approved_df[available_cols],
                disabled=[col for col in available_cols if col != 'Wybierz'],
                hide_index=True,
                use_container_width=True
            )

            selected_rows = edited_df[edited_df["Wybierz"] == True]

            st.write(f"Zaznaczono rekordów: **{len(selected_rows)}** z **{len(approved_df)}**")

            if len(selected_rows) > 0:
                if st.button("🚀 Wygeneruj zaznaczone wnioski (.ZIP)", type="primary"):
                    with st.spinner("Generowanie plików PDF w pamięci..."):
                        zip_buffer = io.BytesIO()

                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                            for idx, row in selected_rows.iterrows():
                                requester = str(row.get('Requester', '')).replace("By ", "").strip()
                                raw_policy = str(row.get('Policy', 'Holidays'))
                                period_str = str(row.get('Time off period', ''))
                                approver_raw = str(row.get('Approved by', '')).replace("By ", "").strip()
                                approver = approver_raw if approver_raw.lower() != 'automatically' else "System (Automatycznie)"
                                notes = str(row.get('Notes', '')) if pd.notna(row.get('Notes')) and str(row.get('Notes')).lower() != 'nan' else ""
                                date_created = str(row.get('Date created', ''))

                                # Tłumaczenie nieobecności
                                policy_pl = translate_policy(raw_policy)

                                # Ustalanie spółki dla pracownika
                                requester_clean_key = requester.lower().strip()
                                comp_type = company_map.get(requester_clean_key, "CRO")
                                company_header_html = get_company_header(comp_type)

                                # Rozróżnienie urlopu od pracy zdalnej / workation
                                policy_lower = raw_policy.lower()
                                is_remote_work = any(term in policy_lower for term in ['home office', 'remote', 'zdalna', 'workation'])

                                if is_remote_work:
                                    doc_title = "Wniosek o pracę zdalną"
                                    request_text = f"Proszę o możliwość wykonywania <strong>pracy zdalnej ({policy_pl})</strong> w okresie:"
                                    type_prefix = "PracaZdalna"
                                else:
                                    doc_title = f"Wniosek – {policy_pl}"
                                    request_text = f"Proszę o udzielenie:<br><strong>{policy_pl}</strong> w okresie:"
                                    type_prefix = sanitize_filename(policy_pl)

                                # Konwersja dat
                                period_pl = parse_english_period_to_pl(period_str)
                                date_created_pl = convert_single_date_to_pl(date_created)

                                notes_html = f"<br><br><em>Uwagi: {notes}</em>" if notes else ""

                                html_content = f"""
                                <!DOCTYPE html>
                                <html lang="pl">
                                <head>
                                    <meta charset="UTF-8">
                                    <style>
                                        @page {{ size: A4; margin: 25mm 20mm; }}
                                        body {{ font-family: Arial, sans-serif; font-size: 11pt; color: #000; line-height: 1.4; }}
                                        .header-company {{ font-size: 10pt; line-height: 1.4; margin-bottom: 40px; }}
                                        .employee-date-table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; }}
                                        .employee-date-table td {{ vertical-align: top; }}
                                        .employee-info {{ width: 50%; }}
                                        
                                        .date-info {{ width: 50%; text-align: right; white-space: nowrap; }}
                                        
                                        .title {{ text-align: center; font-size: 16pt; font-weight: bold; margin: 40px 0 30px 0; text-transform: uppercase; }}
                                        .content-body {{ font-size: 11pt; margin-bottom: 50px; line-height: 1.8; }}
                                        .approval-note-box {{ margin-top: 60px; padding: 15px; border: 1px solid #a0aec0; background-color: #f7fafc; font-size: 10pt; line-height: 1.5; }}
                                        
                                        .date-range {{ white-space: nowrap; }}
                                    </style>
                                </head>
                                <body>

                                <div class="header-company">
                                    {company_header_html}
                                </div>

                                <table class="employee-date-table">
                                    <tr>
                                        <td class="employee-info">
                                            <strong>{requester}</strong><br>
                                            <span style="font-size: 9pt; color: #555;">Imię i nazwisko pracownika</span>
                                        </td>
                                        <td class="date-info">
                                            {city_input},\u00A0dnia\u00A0{date_created_pl}\u00A0r.
                                        </td>
                                    </tr>
                                </table>

                                <div class="title">{doc_title}</div>

                                <div class="content-body">
                                    {request_text} <strong class="date-range">{period_pl}</strong>.
                                </div>

                                <div class="approval-note-box">
                                    <strong>Adnotacja o zatwierdzeniu elektronicznym:</strong><br>
                                    Dokument został wygenerowany automatycznie na podstawie danych z elektronicznego systemu wnioskowego z Trackingtime.<br>
                                    Wniosek został zaakceptowany przez: <strong>{approver}</strong>.
                                    {notes_html}
                                </div>

                                </body>
                                </html>
                                """

                                pdf_bytes = HTML(string=html_content).write_pdf()

                                # Nazewnictwo plików: [Spółka]_[Typ]_[Nazwisko_Imię]_[YYYY-MM-DD].pdf
                                clean_person = sanitize_filename(requester)
                                date_num = extract_numeric_date_for_filename(period_str)
                                
                                filename = f"{comp_type}_{type_prefix}_{clean_person}_{date_num}.pdf"
                                
                                zip_file.writestr(filename, pdf_bytes)

                    st.download_button(
                        label="📥 Pobierz wybraną selekcję (.ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="Wnioski_SCIENTIA.zip",
                        mime="application/zip",
                        type="primary"
                    )
            else:
                st.warning("Nie zaznaczono żadnego wniosku z listy.")

        else:
            st.warning("Plik nie zawiera żadnych zaakceptowanych wniosków.")

    except Exception as e:
        st.error(f"Błąd podczas przetwarzania pliku: {e}")