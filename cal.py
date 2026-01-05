import streamlit as st
import pandas as pd
import pdfplumber
import re
import os

# === 설정: 이미지 및 파일 경로 ===
IMG_MASCOT = "fin_mascot.png"
IMG_LOGO_SMALL = "fin_logo_small.png"
IMG_LOGO_FULL = "fin_logo_full.png"

# CSV 파일명 정의 (사용자가 업로드한 파일명 기준)
FILE_RATES = "핀모든_2026_01_05.xlsx - 담보대출  전세대출 금리산식.csv"
FILE_PARTNERS = "핀모든_2026_01_05.xlsx - 거래처  광고.csv"
FILE_CLIENTS = "핀모든_2026_01_05.xlsx - 안재용.csv" # 예시 고객 파일

# === [기능 1] KB 시세 조회 매니저 (Mock) ===
class KBPriceManager:
    """
    실제 KB부동산 크롤링은 캡차(Captcha) 등으로 인해 로컬 셀레니움 환경이 필요합니다.
    여기서는 주소를 입력받아 시세를 보여주는 UI 구조를 구현하고, 
    실제 데이터 연동 위치를 표시했습니다.
    """
    def get_price(self, address):
        # TODO: 여기에 실제 selenium 또는 requests 크롤링 코드를 넣습니다.
        # 현재는 데모용으로 주소에 따라 다른 값을 리턴하거나 고정값을 줍니다.
        if "정자동" in address:
            return 1360000000, "KB부동산 일반평균가 (업데이트: 2026-01-05)"
        elif "대치동" in address:
            return 2500000000, "KB부동산 일반평균가 (업데이트: 2026-01-05)"
        else:
            return 850000000, "KB부동산 추정 시세 (표본 부족)"

# === [기능 2] PDF 등기부등본 분석기 ===
class PDFRegistryAnalyzer:
    def analyze(self, uploaded_file):
        text_content = ""
        summary = {"소유자": [], "근저당": [], "주소": "식별 불가"}
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text_content += page.extract_text() + "\n"
        
        # 1. 표제부 (주소) 찾기
        addr_match = re.search(r"건물내역\s+([^\n]+)", text_content)
        if addr_match:
            summary["주소"] = addr_match.group(1).strip()
            
        # 2. 갑구 (소유권) 분석 - 단순화된 로직
        # '소유자' 키워드 뒤의 이름을 찾습니다.
        owners = re.findall(r"소유자\s+([가-힣]+)", text_content)
        if owners:
            summary["소유자"] = list(set(owners)) # 중복 제거
            
        # 3. 을구 (근저당) 분석
        # '채권최고액 금' 패턴을 찾습니다.
        debts = re.findall(r"채권최고액\s+금([0-9,]+)원", text_content)
        if debts:
            # 문자열 금액을 숫자로 변환하여 저장
            summary["근저당"] = [int(d.replace(",", "")) for d in debts]
            
        return summary, text_content

# === [기능 3] 금융 계산기 (엑셀 수식 연동) ===
class MortgageCalculator:
    def __init__(self):
        # 기본값 설정 (파일 로드 실패 시 사용)
        self.default_rates = {
            "국민은행": 0.0447, "신한은행": 0.0447, 
            "우리은행": 0.0445, "하나은행": 0.0463
        }
        self.load_rates_from_csv()

    def load_rates_from_csv(self):
        try:
            if os.path.exists(FILE_RATES):
                df = pd.read_csv(FILE_RATES)
                # CSV 구조에 맞춰 파싱 (실제 파일 구조에 따라 인덱스 조정 필요)
                # 여기서는 '금융사' 컬럼이나 특정 위치를 찾아 매핑한다고 가정
                # 업로드된 파일의 [1, 13] 위치 등이 국민은행 금리라고 가정 (분석 기반)
                # 실제로는 더 정교한 파싱이 필요하나, 예시로 하드코딩된 위치를 참조
                pass 
        except Exception as e:
            st.error(f"금리 파일 로드 중 오류: {e}")

    def calculate(self, loan_amount, bank_name, ltv_ratio=0.8):
        # 선택된 은행의 금리 가져오기
        rate = self.default_rates.get(bank_name, 0.05)
        
        limit = loan_amount * ltv_ratio # 단순 예시
        interest_monthly = (loan_amount * rate) / 12
        
        return {
            "bank": bank_name,
            "rate": rate * 100,
            "interest": int(interest_monthly)
        }

# === 메인 앱 구조 ===
def main():
    st.set_page_config(
        page_title="핀모든 통합 관리 시스템", 
        page_icon=IMG_LOGO_SMALL, 
        layout="wide"
    )

    # 상단 배너
    try:
        st.image(IMG_LOGO_FULL, width=250)
    except:
        st.title("🏦 핀모든 통합 관리 시스템")

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["🧮 대출 통합 계산기", "📄 등기부 PDF 분석", "⚙️ 관리자 페이지"])

    # --- TAB 1: 계산기 및 시세 조회 ---
    with tab1:
        st.subheader("🏡 KB시세 조회 및 대출 계산")
        col_addr, col_info = st.columns([2, 1])
        
        with col_addr:
            address_input = st.text_input("부동산 주소 입력 (예: 분당구 정자동 한솔마을)", value="분당구 정자동 112")
            if st.button("KB 시세 조회"):
                kb_manager = KBPriceManager()
                price, info = kb_manager.get_price(address_input)
                st.session_state['kb_price'] = price
                st.success(f"**{info}**: {price/100000000:.2f}억 원")
        
        st.markdown("---")
        
        # 계산기 UI
        st.write("#### 💰 대출 조건 시뮬레이션")
        c1, c2, c3 = st.columns(3)
        with c1:
            loan_amt = st.number_input("대출 신청 금액 (원)", value=500000000, step=10000000)
        with c2:
            target_bank = st.selectbox("금융사 선택", ["국민은행", "신한은행", "우리은행", "하나은행"])
        with c3:
            loan_type = st.radio("대출 종류", ["매매자금", "생활안정자금", "전세자금"])

        if st.button("대출 계산 실행"):
            calc = MortgageCalculator()
            res = calc.calculate(loan_amt, target_bank)
            
            st.info(f"""
            **[{res['bank']}] 분석 결과**
            - 적용 금리: **{res['rate']:.2f}%** (변동/고정 혼합 기준)
            - 월 예상 이자: **{res['interest']:,}원**
            """)

    # --- TAB 2: PDF 분석 ---
    with tab2:
        st.subheader("📑 부동산 등기부등본(PDF) 분석")
        st.caption("PDF 파일을 업로드하면 주요 권리 관계(소유자, 채권최고액 등)를 자동으로 추출합니다.")
        
        uploaded_pdf = st.file_uploader("등기부등본 PDF 업로드", type=["pdf"])
        if uploaded_pdf:
            with st.spinner("PDF 문서를 스캔하고 내용을 분석 중입니다..."):
                analyzer = PDFRegistryAnalyzer()
                summary, raw_text = analyzer.analyze(uploaded_pdf)
                
                st.markdown("### 🔍 분석 요약")
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("부동산 주소", summary["주소"])
                col_p1.caption("(표제부 추정)")
                
                owners_str = ", ".join(summary["소유자"]) if summary["소유자"] else "확인 필요"
                col_p2.metric("현재 소유자", owners_str)
                col_p2.caption("(갑구)")
                
                total_debt = sum(summary["근저당"])
                col_p3.metric("총 설정액(채권최고액)", f"{total_debt:,}원")
                col_p3.caption(f"(을구 - 건수: {len(summary['근저당'])}건)")
                
                with st.expander("PDF 원문 텍스트 보기"):
                    st.text(raw_text)

    # --- TAB 3: 관리자 페이지 ---
    with tab3:
        st.subheader("⚙️ 관리자 데이터 센터")
        
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["거래처 관리", "고객 관리", "광고 관리"])
        
        # 1. 거래처/광고 데이터 로드
        try:
            df_partners = pd.read_csv(FILE_PARTNERS)
        except:
            df_partners = pd.DataFrame({"거래처명": ["예시거래처"], "연락처": ["010-0000-0000"]})

        # 2. 고객 데이터 로드
        try:
            df_clients = pd.read_csv(FILE_CLIENTS)
        except:
            df_clients = pd.DataFrame({"고객명": ["홍길동"], "대출금액": [100000000]})

        with admin_tab1:
            st.write("### 🏢 거래처 목록")
            edited_partners = st.data_editor(df_partners, num_rows="dynamic", use_container_width=True)
            if st.button("거래처 변경사항 저장"):
                edited_partners.to_csv(FILE_PARTNERS, index=False)
                st.success("저장되었습니다.")

        with admin_tab2:
            st.write("### 👥 고객 관리 리스트")
            # 주요 컬럼만 보여주거나 전체 보여주기
            st.dataframe(df_clients, use_container_width=True)
            
        with admin_tab3:
            st.write("### 📢 광고 집행 현황")
            # 거래처 파일 내에 광고 정보가 있다고 가정하고 필터링해서 보여줌
            if '광고' in df_partners.columns or '비용' in df_partners.columns:
                st.bar_chart(df_partners.set_index('명칭')[['월비용']])
            else:
                st.info("광고 비용 데이터가 없습니다.")

    # 하단 푸터
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey;'>System powered by 핀모든 v2.0</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
