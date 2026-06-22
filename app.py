import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
import re

st.set_page_config(
    page_title="MEDEK PÇ İzleme Sistemi",
    layout="wide"
)

st.title("MEDEK Program Çıktısı İzleme ve Değerlendirme Sistemi")

st.write(
    """
    Bu uygulama, ders sorumlularının kendi dersleri için program çıktısı başarı düzeylerini
    öğrenci numarası bazında hesaplaması ve dönem sonu raporu üretmesi amacıyla hazırlanmıştır.
    Öğrenci adı ve soyadı kullanılmaz; yalnızca öğrenci numarası ile işlem yapılır.
    """
)

# ---------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------

def temiz_sutun_adi(col):
    """
    OBS çıktısında sütun adları Öğrenci No_5234FK, HBN_5234FK gibi gelebilir.
    Bu fonksiyon sondaki ekleri temizler.
    """
    col = str(col).strip()
    col = re.sub(r"_.*$", "", col)
    return col.strip()


def obs_verisini_duzenle(df):
    """
    OBS Excel veya kopyala-yapıştır verisinden öğrenci no ve HBN/ders başarı notunu otomatik bulur.
    Ad-soyad alanlarını dikkate almaz.
    """

    df = df.copy()
    df.columns = [temiz_sutun_adi(c) for c in df.columns]

    ogrenci_no_col = None
    not_col = None

    for col in df.columns:
        col_lower = str(col).lower()

        if "öğrenci no" in col_lower or "ogrenci no" in col_lower or col_lower == "öğrenci no":
            ogrenci_no_col = col

        if col_lower == "hbn" or "hbn" in col_lower:
            not_col = col

    if ogrenci_no_col is None:
        for col in df.columns:
            col_lower = str(col).lower()
            if "no" in col_lower and "öğrenci" in col_lower:
                ogrenci_no_col = col

    if not_col is None:
        for col in df.columns:
            col_lower = str(col).lower()
            if "ders başarı" in col_lower or "başarı notu" in col_lower or "basari notu" in col_lower:
                not_col = col

    if ogrenci_no_col is None or not_col is None:
        return None, ogrenci_no_col, not_col

    sonuc = df[[ogrenci_no_col, not_col]].copy()
    sonuc.columns = ["Öğrenci No", "Ders Başarı Notu"]

    sonuc["Öğrenci No"] = sonuc["Öğrenci No"].astype(str).str.strip()
    sonuc["Ders Başarı Notu"] = pd.to_numeric(sonuc["Ders Başarı Notu"], errors="coerce")

    sonuc = sonuc.dropna(subset=["Öğrenci No", "Ders Başarı Notu"])
    sonuc = sonuc[sonuc["Öğrenci No"] != ""]
    sonuc = sonuc.reset_index(drop=True)

    return sonuc, ogrenci_no_col, not_col


def durum_belirle(puan, ulasti_esigi, kismen_esigi):
    if puan >= ulasti_esigi:
        return "Ulaştı"
    elif puan >= kismen_esigi:
        return "Kısmen ulaştı"
    else:
        return "Geliştirilmesi gerekir"


def genel_degerlendirme(ortalama, ulasti_esigi, kismen_esigi):
    if ortalama >= ulasti_esigi:
        return "Yeterli"
    elif ortalama >= kismen_esigi:
        return "İzlenmeli"
    else:
        return "İyileştirme gerekli"


# ---------------------------------------------------------
# Ders Bilgileri
# ---------------------------------------------------------

st.sidebar.header("Ders Bilgileri")

ders_adi = st.sidebar.text_input("Ders Adı", "Hidrolik ve Pnömatik Sistemler")
ders_kodu = st.sidebar.text_input("Ders Kodu", "MEK")
donem = st.sidebar.text_input("Dönem", "2025-2026 Güz")
ders_sorumlusu = st.sidebar.text_input("Ders Sorumlusu", "")

st.sidebar.header("Başarı Eşikleri")

ulasti_esigi = st.sidebar.number_input(
    "Ulaştı eşiği",
    min_value=0,
    max_value=100,
    value=70
)

kismen_esigi = st.sidebar.number_input(
    "Kısmen ulaştı eşiği",
    min_value=0,
    max_value=100,
    value=50
)

# ---------------------------------------------------------
# PÇ Açıklamaları
# ---------------------------------------------------------

st.header("1. Dersin Program Çıktılarına Katkı Düzeyini Giriniz")

st.info(
    """
    Her PÇ için 0-5 arasında katkı düzeyi giriniz.
    
    0 = İlişki yok  
    1 = Çok düşük katkı  
    2 = Düşük katkı  
    3 = Orta katkı  
    4 = Yüksek katkı  
    5 = Çok yüksek katkı
    """
)

pc_aciklamalari = {
    "PÇ1": "Mesleği ile ilgili temel, güncel ve uygulamalı bilgilere sahiptir.",
    "PÇ2": "İş sağlığı ve güvenliği, çevre bilinci ve kalite süreçleri hakkında bilgi sahibi olur.",
    "PÇ3": "Matematik, fen bilimleri ve mekatronik alanında yeterli altyapıya sahip olur; makine elemanlarını tanır, hesaplama yapar ve mekanik sistemleri tasarlar.",
    "PÇ4": "Mekatronik ile ilgili temel kavramları tanımlar ve uygular.",
    "PÇ5": "Güncel teknolojik gelişmeleri ve mesleki uygulamaları takip eder, etkin biçimde kullanır.",
    "PÇ6": "Mesleği ile ilgili bilişim teknolojilerini, yazılım, program ve araçları etkin şekilde kullanır.",
    "PÇ7": "Mesleki problemleri analitik ve eleştirel bir yaklaşımla değerlendirir, çözüm önerileri geliştirir.",
    "PÇ8": "Hidrolik ve pnömatik sistem elemanlarını ve otomasyon sistem elemanlarını tanımlar ve sistemi tasarlar.",
    "PÇ9": "Bilgi ve becerilerini Türkçe ve yabancı dilde yazılı ve sözlü olarak ifade eder.",
    "PÇ10": "Karmaşık sorunları çözmek için ekip üyesi olarak etkin şekilde sorumluluk alır.",
    "PÇ11": "Kariyer yönetimi, yaşam boyu öğrenme, etik ve kültürel değerlere karşı farkındalığa sahiptir.",
    "PÇ12": "Verilerin toplanması, uygulanması ve sonuçların duyurulmasında toplumsal, bilimsel, kültürel ve etik değerlere sahiptir."
}

pc_katki = {}

for pc, aciklama in pc_aciklamalari.items():
    pc_katki[pc] = st.selectbox(
        f"{pc} - {aciklama}",
        options=[0, 1, 2, 3, 4, 5],
        index=0
    )

aktif_pcler = [pc for pc, katkı in pc_katki.items() if katkı > 0]

if aktif_pcler:
    st.success("Bu ders için ilişkilendirilen program çıktıları: " + ", ".join(aktif_pcler))
else:
    st.warning("Henüz hiçbir program çıktısı seçilmedi.")

# ---------------------------------------------------------
# Ölçme-Değerlendirme Bilgileri
# ---------------------------------------------------------

st.header("2. Ölçme-Değerlendirme Bilgisi")

olcme_turu = st.multiselect(
    "Bu derste kullanılan ölçme-değerlendirme araçlarını seçiniz",
    [
        "Ara sınav",
        "Final sınavı",
        "Bütünleme sınavı",
        "Ödev",
        "Proje",
        "Uygulama",
        "Laboratuvar çalışması",
        "Teknik çizim",
        "Devre tasarımı",
        "Kodlama çalışması",
        "Teknik rapor",
        "Sunum",
        "Performans değerlendirme"
    ],
    default=["Ara sınav", "Final sınavı"]
)

kanit_aciklamasi = st.text_area(
    "Bu ders için sunulacak kanıtları kısaca yazınız",
    "Sınav kâğıtları, cevap anahtarları, ödev/proje dosyaları, uygulama çalışmaları, çizimler, teknik raporlar ve değerlendirme formları."
)

# ---------------------------------------------------------
# Öğrenci Verisi Girişi
# ---------------------------------------------------------

st.header("3. OBS Verisini Yükleyiniz veya Yapıştırınız")

veri_giris_yontemi = st.radio(
    "Veri giriş yöntemini seçiniz",
    [
        "OBS Excel dosyası yükle",
        "OBS tablosunu kopyala-yapıştır",
        "Manuel giriş"
    ]
)

ogrenci_df = None

if veri_giris_yontemi == "OBS Excel dosyası yükle":
    st.write("OBS’den aldığınız Excel dosyasını buraya yükleyiniz. Sistem Öğrenci No ve HBN sütunlarını otomatik alacaktır.")

    uploaded_file = st.file_uploader(
        "OBS Excel dosyası yükle",
        type=["xlsx", "xls"]
    )

    if uploaded_file is not None:
        try:
            obs_df = pd.read_excel(uploaded_file)
            ogrenci_df, ogr_col, not_col = obs_verisini_duzenle(obs_df)

            if ogrenci_df is None:
                st.error("Öğrenci No veya HBN sütunu bulunamadı. Lütfen OBS dosyasını kontrol ediniz.")
                st.write("Bulunan sütunlar:")
                st.write(list(obs_df.columns))
            else:
                st.success(f"Veri başarıyla okundu. Kullanılan sütunlar: {ogr_col} ve {not_col}")
                st.dataframe(ogrenci_df, use_container_width=True)

        except Exception as e:
            st.error("Excel dosyası okunurken hata oluştu.")
            st.write(e)

elif veri_giris_yontemi == "OBS tablosunu kopyala-yapıştır":
    st.write(
        """
        OBS Excel dosyasındaki tabloyu başlık satırıyla birlikte kopyalayıp aşağıdaki kutuya yapıştırınız.
        Sistem Öğrenci No ve HBN sütunlarını otomatik alacaktır.
        """
    )

    yapistirilan_veri = st.text_area(
        "OBS tablosunu buraya yapıştırınız",
        height=250
    )

    if yapistirilan_veri.strip() != "":
        try:
            obs_df = pd.read_csv(StringIO(yapistirilan_veri), sep="\t")
            ogrenci_df, ogr_col, not_col = obs_verisini_duzenle(obs_df)

            if ogrenci_df is None:
                st.error("Öğrenci No veya HBN sütunu bulunamadı. Lütfen tabloyu başlık satırıyla birlikte yapıştırınız.")
                st.write("Bulunan sütunlar:")
                st.write(list(obs_df.columns))
            else:
                st.success(f"Veri başarıyla okundu. Kullanılan sütunlar: {ogr_col} ve {not_col}")
                st.dataframe(ogrenci_df, use_container_width=True)

        except Exception as e:
            st.error("Yapıştırılan veri okunurken hata oluştu.")
            st.write(e)

else:
    st.write("Öğrenci adı yazılmayacaktır. Yalnızca öğrenci numarası ve ders başarı notu giriniz.")

    ornek_veri = pd.DataFrame(
        {
            "Öğrenci No": ["001", "002", "003"],
            "Ders Başarı Notu": [75, 68, 82]
        }
    )

    ogrenci_df = st.data_editor(
        ornek_veri,
        num_rows="dynamic",
        use_container_width=True
    )

    ogrenci_df["Ders Başarı Notu"] = pd.to_numeric(
        ogrenci_df["Ders Başarı Notu"],
        errors="coerce"
    )

    ogrenci_df = ogrenci_df.dropna(subset=["Öğrenci No", "Ders Başarı Notu"])

# ---------------------------------------------------------
# Raporlama
# ---------------------------------------------------------

st.header("4. Rapor Oluştur")

if st.button("Raporu Hesapla"):
    if len(aktif_pcler) == 0:
        st.error("En az bir program çıktısı için katkı düzeyi girilmelidir.")

    elif ogrenci_df is None or ogrenci_df.empty:
        st.error("Öğrenci notları yüklenmeli, yapıştırılmalı veya manuel girilmelidir.")

    else:
        sonuc_df = ogrenci_df.copy()

        for pc in aktif_pcler:
            sonuc_df[pc] = sonuc_df["Ders Başarı Notu"]
            sonuc_df[f"{pc} Durum"] = sonuc_df[pc].apply(
                lambda x: durum_belirle(x, ulasti_esigi, kismen_esigi)
            )

        st.subheader("Öğrenci Bazlı Program Çıktısı Başarı Sonuçları")
        st.dataframe(sonuc_df, use_container_width=True)

        rapor_satirlari = []

        for pc in aktif_pcler:
            ortalama = sonuc_df[pc].mean()
            ulasti_orani = (sonuc_df[pc] >= ulasti_esigi).mean() * 100
            kismen_orani = (
                (sonuc_df[pc] >= kismen_esigi) &
                (sonuc_df[pc] < ulasti_esigi)
            ).mean() * 100
            gelistirilmeli_orani = (sonuc_df[pc] < kismen_esigi).mean() * 100

            rapor_satirlari.append(
                {
                    "Ders Kodu": ders_kodu,
                    "Ders Adı": ders_adi,
                    "Dönem": donem,
                    "Ders Sorumlusu": ders_sorumlusu,
                    "Program Çıktısı": pc,
                    "PÇ Açıklaması": pc_aciklamalari[pc],
                    "Dersin PÇ Katkı Düzeyi": pc_katki[pc],
                    "Öğrenci Sayısı": len(sonuc_df),
                    "Ortalama Başarı": round(ortalama, 2),
                    "Ulaşan Öğrenci Oranı (%)": round(ulasti_orani, 2),
                    "Kısmen Ulaşan Oranı (%)": round(kismen_orani, 2),
                    "Geliştirilmesi Gereken Oran (%)": round(gelistirilmeli_orani, 2),
                    "Genel Değerlendirme": genel_degerlendirme(
                        ortalama,
                        ulasti_esigi,
                        kismen_esigi
                    )
                }
            )

        rapor_df = pd.DataFrame(rapor_satirlari)

        st.subheader("Ders Bazlı Program Çıktısı Genel Raporu")
        st.dataframe(rapor_df, use_container_width=True)

        st.subheader("Rapor Metni")

        rapor_metni = f"""
{donem} döneminde {ders_adi} dersi kapsamında program çıktılarının sağlanma düzeyi öğrenci numarası bazlı olarak değerlendirilmiştir. 
Dersin ilişkilendirildiği program çıktıları {", ".join(aktif_pcler)} olarak belirlenmiştir. 
Ölçme-değerlendirme sürecinde {", ".join(olcme_turu)} araçları kullanılmıştır. 
Öğrenci başarı notları üzerinden ilgili program çıktıları için ortalama başarı, ulaşan öğrenci oranı, kısmen ulaşan öğrenci oranı ve geliştirilmesi gereken öğrenci oranı hesaplanmıştır. 
Değerlendirme sürecinde öğrenci adları kullanılmamış, yalnızca öğrenci numarası bazlı veriler esas alınmıştır. 
Elde edilen sonuçlar ders bazlı program çıktısı değerlendirme raporuna dönüştürülmüş ve dönemsel izleme kapsamında kayıt altına alınmıştır.
"""

        st.write(rapor_metni)

        st.subheader("İyileştirme Önerileri")

        iyilestirme_df = rapor_df[
            rapor_df["Genel Değerlendirme"] != "Yeterli"
        ].copy()

        if iyilestirme_df.empty:
            st.success("Bu ders kapsamında seçilen program çıktılarında beklenen başarı düzeyine ulaşılmıştır.")
        else:
            iyilestirme_df["İyileştirme Önerisi"] = (
                "İlgili PÇ için uygulama, ödev, proje, örnek çalışma veya destekleyici etkinlik artırılmalıdır."
            )
            st.dataframe(iyilestirme_df, use_container_width=True)

        st.subheader("Kanıt Açıklaması")
        st.write(kanit_aciklamasi)

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    "Alan": [
                        "Ders Kodu",
                        "Ders Adı",
                        "Dönem",
                        "Ders Sorumlusu",
                        "Rapor Tarihi"
                    ],
                    "Değer": [
                        ders_kodu,
                        ders_adi,
                        donem,
                        ders_sorumlusu,
                        datetime.now().strftime("%d.%m.%Y")
                    ]
                }
            ).to_excel(writer, sheet_name="Ders_Bilgileri", index=False)

            pd.DataFrame(
                {
                    "Program Çıktısı": list(pc_katki.keys()),
                    "PÇ Açıklaması": list(pc_aciklamalari.values()),
                    "Katkı Düzeyi": list(pc_katki.values())
                }
            ).to_excel(writer, sheet_name="PÇ_Katkı_Düzeyi", index=False)

            pd.DataFrame(
                {
                    "Ölçme-Değerlendirme Araçları": olcme_turu,
                }
            ).to_excel(writer, sheet_name="Ölçme_Araçları", index=False)

            ogrenci_df.to_excel(writer, sheet_name="Öğrenci_Notları", index=False)
            sonuc_df.to_excel(writer, sheet_name="Öğrenci_PÇ_Sonuçları", index=False)
            rapor_df.to_excel(writer, sheet_name="PÇ_Genel_Rapor", index=False)

            if not iyilestirme_df.empty:
                iyilestirme_df.to_excel(writer, sheet_name="İyileştirme_Planı", index=False)

            pd.DataFrame(
                {
                    "Rapor Metni": [rapor_metni],
                    "Kanıt Açıklaması": [kanit_aciklamasi]
                }
            ).to_excel(writer, sheet_name="Rapor_Metni", index=False)

        st.download_button(
            label="Excel Raporunu İndir",
            data=output.getvalue(),
            file_name=f"{ders_kodu}_{ders_adi}_PC_Raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
