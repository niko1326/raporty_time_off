import streamlit as st
import pandas as pd
from weasyprint import HTML
import io
import zipfile

st.set_page_config(
    page_title="Generator Wniosków Urlopowych - SCIENTIA",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Generator Wniosków Urlopowych - SCIENTIA")
st.markdown("Wgraj plik raportu, wybierz wnioski z listy i wygeneruj gotowe PDF-y dla Kadr / PIP.")

# Wybór spółki
company_option = st.selectbox(
    "Wybierz spółkę dla generowanych wniosków:",
    ["SCIENTIA CRO Sp. z o.o.", "SCIENTIA RESEARCH INSTITUTE Sp. z o.o."]
)

if company_option == "SCIENTIA CRO Sp. z o.o.":
    company_header_html = """
        <strong>SCIENTIA CRO Sp. z o.o.</strong><br>
        ul. Ogińskiego 2, 85-092 Bydgoszcz<br>
        KRS 0000999674 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; NIP 9671460288 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; REGON 523240305
    """
else:
    company_header_html = """
        <strong>SCIENTIA RESEARCH INSTITUTE Sp. z o.o.</strong><br>
        ul. Michała Kleofasa Ogińskiego 2, 85-092 Bydgoszcz<br>
        NIP: 9532779052 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; REGON: 387251647 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; KRS: 0000864098
    """

# Wgrywanie pliku
uploaded_file = st.file_uploader("Wgraj plik raportu (.xlsx lub .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Filtrowanie tylko statusu APPROVED
        if 'Status' in df.columns:
            approved_df = df[df['Status'].astype(str).str.upper() == 'APPROVED'].copy().reset_index(drop=True)
        else:
            st.error("Plik nie zawiera wymaganej kolumny 'Status'.")
            approved_df = pd.DataFrame()

        if not approved_df.empty:
            st.success(f"Znaleziono **{len(approved_df)}** zaakceptowanych wniosków.")

            st.subheader("📋 Wybierz rekordy do wygenerowania:")
            
            # Tabela z checkboxami do selekcji rekordów
            approved_df.insert(0, "Wybierz", True) # Domyślnie zaznaczone wszystkie
            
            edited_df = st.data_editor(
                approved_df[['Wybierz', 'Date created', 'Requester', 'Policy', 'Time off period', 'Approved by', 'Notes']],
                disabled=['Date created', 'Requester', 'Policy', 'Time off period', 'Approved by', 'Notes'],
                hide_index=True,
                use_container_width=True
            )

            # Przefiltrowanie tylko wybranych przez użytkownika
            selected_rows = edited_df[edited_df["Wybierz"] == True]

            st.write(f"Zaznaczono rekordów: **{len(selected_rows)}** z **{len(approved_df)}**")

            if len(selected_rows) > 0:
                if st.button("🚀 Wygeneruj zaznaczone wnioski (.ZIP)", type="primary"):
                    with st.spinner("Generowanie plików PDF w pamięci..."):
                        zip_buffer = io.BytesIO()

                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                            for idx, row in selected_rows.iterrows():
                                requester = str(row.get('Requester', '')).replace("By ", "").strip()
                                policy = str(row.get('Policy', 'Holidays'))
                                period_str = str(row.get('Time off period', ''))
                                approver = str(row.get('Approved by', '')).replace("By ", "").strip()
                                notes = str(row.get('Notes', '')) if pd.notna(row.get('Notes')) and str(row.get('Notes')).lower() != 'nan' else ""
                                date_created = str(row.get('Date created', ''))

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
                                        .employee-info {{ width: 60%; }}
                                        .date-info {{ width: 40%; text-align: right; }}
                                        .title {{ text-align: center; font-size: 16pt; font-weight: bold; margin: 40px 0 30px 0; text-transform: uppercase; }}
                                        .content-body {{ font-size: 11pt; margin-bottom: 50px; line-height: 1.8; }}
                                        .approval-note-box {{ margin-top: 60px; padding: 15px; border: 1px solid #a0aec0; background-color: #f7fafc; font-size: 10pt; line-height: 1.5; }}
                                        .footer-asterisk {{ margin-top: 80px; font-size: 9pt; color: #4a5568; }}
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
                                            dnia {date_created} r.
                                        </td>
                                    </tr>
                                </table>

                                <div class="title">Wniosek o urlop</div>

                                <div class="content-body">
                                    Proszę o udzielenie:<br>
                                    <strong>Urlopu wypoczynkowego ({policy})</strong> w okresie: <strong>{period_str}</strong>.
                                </div>

                                <div class="approval-note-box">
                                    <strong>Adnotacja o zatwierdzeniu elektronicznym:</strong><br>
                                    Dokument został wygenerowany automatycznie na podstawie danych z elektronicznego systemu wnioskowego.<br>
                                    Wniosek został zaakceptowany przez: <strong>{approver}</strong>.
                                    {notes_html}
                                </div>

                                <div class="footer-asterisk">
                                    *skreśl niewłaściwe
                                </div>

                                </body>
                                </html>
                                """

                                pdf_bytes = HTML(string=html_content).write_pdf()
                                clean_name = requester.replace(" ", "_")
                                filename = f"Wniosek_{clean_name}_{idx+1}.pdf"
                                
                                zip_file.writestr(filename, pdf_bytes)

                    st.download_button(
                        label="📥 Pobierz wybraną selekcję (.ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="Wnioski_Urlopowe_SCIENTIA.zip",
                        mime="application/zip",
                        type="primary"
                    )
            else:
                st.warning("Nie zaznaczono żadnego wniosku z listy.")

        else:
            st.warning("Plik nie zawiera żadnych rekordów ze statusem 'APPROVED'.")

    except Exception as e:
        st.error(f"Błąd podczas przetwarzania pliku: {e}")