import streamlit as st
import pandas as pd

# === 설정: 이미지 파일 경로 지정 ===
# 실제 이미지 파일이 있는 경로와 일치해야 합니다.
# 파이썬 스크립트와 같은 폴더에 이미지를 두는 것을 권장합니다.
IMG_MASCOT = "fin_mascot.png"       # image_1.png (고양이 마스코트)
IMG_LOGO_SMALL = "fin_logo_small.png" # image_2.png (작은 심볼)
IMG_LOGO_FULL = "fin_logo_full.png"   # image_3.png (전체 로고 + 슬로건)
# ==================================

class MortgageCalculator:
    def __init__(self):
        # 2026-01-02 기준: 금융사별 가이드라인 (예시 데이터)
        self.banks = {
            "애큐온저축은행": {"ltv_max": 0.85, "rate_min": 5.8, "rate_max": 6.9, "name": "애큐온"},
            "키움예스저축은행": {"ltv_max": 0.85, "rate_min": 6.5, "rate_max": 7.8, "name": "키움Yes"},
            "OK저축은행": {"ltv_max": 0.90, "rate_min": 7.5, "rate_max": 9.5, "name": "OK저축"},
            "SBI저축은행": {"ltv_max": 0.80, "rate_min": 5.9, "rate_max": 7.2, "name": "SBI"},
            "애큐온캐피탈": {"ltv_max": 0.80, "rate_min": 6.2, "rate_max": 7.5, "name": "애큐온CAP"}
        }
        
        # 지역별 소액임차보증금 (2025년 기준 가정)
        self.room_deduction_map = {
            "서울": 55000000,
            "과밀억제권역(경기/인천 등)": 48000000,
            "광역시": 28000000,
            "그외": 25000000
        }

    def estimate_rate(self, bank_rules, credit_score):
        """
        신용점수(NICE 기준)에 따른 예상 금리 계산 (선형 보간)
        """
        min_score = 600
        max_score = 1000
        
        # 점수 보정
        score = max(min_score, min(credit_score, max_score))
        
        # 점수가 높을수록 금리가 낮아지도록 비율 계산
        ratio = 1 - ((score - min_score) / (max_score - min_score))
        
        estimated = bank_rules['rate_min'] + (bank_rules['rate_max'] - bank_rules['rate_min']) * ratio
        return round(estimated, 2)

    def calculate(self, kb_price, existing_loan, loan_type, region_type, 
                  is_trust_mci, credit_score, bond_max_ratio):
        
        results = []
        deduction_price = self.room_deduction_map.get(region_type, 25000000)

        for bank_name, rules in self.banks.items():
            # 1. LTV 한도
            ltv_limit = kb_price * rules['ltv_max']

            # 2. 방공제 적용 (신탁/MCI면 0원)
            real_deduction = 0 if is_trust_mci else deduction_price
            
            # 3. 이론적 최대 한도
            max_limit = ltv_limit - real_deduction

            # 4. 자금 계산 (대환 vs 후순위)
            if loan_type == "대환":
                # 대환: 기존 대출 상환 후 남는 금액
                available_limit = max_limit
                net_cash = max_limit - existing_loan
            else:
                # 후순위: 기존 대출 채권최고액을 뺀 나머지
                senior_bond_amount = existing_loan * bond_max_ratio
                available_limit = max_limit - senior_bond_amount
                net_cash = available_limit

            # 5. 금리 추정
            est_rate = self.estimate_rate(rules, credit_score)

            if net_cash > 0:
                results.append({
                    "금융사": bank_name,
                    "적용 LTV": f"{rules['ltv_max']*100:.0f}%",
                    "예상 금리(%)": est_rate,  # 정렬을 위해 숫자형 유지
                    "총 한도(만원)": int(available_limit / 10000),
                    "추가 확보금(만원)": int(net_cash / 10000),
                    "금리 범위": f"{rules['rate_min']}~{rules['rate_max']}%"
                })

        if not results:
            return pd.DataFrame()
            
        df = pd.DataFrame(results)
        
        # 정렬: 추가 확보금 많은 순 -> 금리 낮은 순
        df = df.sort_values(by=["추가 확보금(만원)", "예상 금리(%)"], ascending=[False, True])
        
        return df

# --- Streamlit UI 구성 ---
def main():
    # [Brand update] 페이지 설정에 파비콘(page_icon) 추가
    st.set_page_config(
        page_title="핀모든 - 사업자 주택담보대출 계산기", 
        page_icon=IMG_LOGO_SMALL, 
        layout="wide"
    )
    
    # [Brand update] 메인 상단 배너 이미지 적용
    try:
        st.image(IMG_LOGO_FULL, width=300) # 전체 로고를 깔끔하게 배치
    except FileNotFoundError:
        st.warning("⚠️ 로고 이미지 파일이 없습니다. 경로를 확인해주세요.")
        st.title("🏗️ 사업자 주택담보대출 통합계산기")

    st.markdown("### 💼 실사업자를 위한 스마트한 대출 비교 솔루션")
    st.markdown("---")

    # 사이드바: 입력 폼
    with st.sidebar:
        # [Brand update] 사이드바 상단 마스코트 적용
        try:
            st.image(IMG_MASCOT, use_column_width=True)
            st.markdown("<div style='text-align: center; color: gray; margin-bottom: 20px;'>▲ 핀모든 AI 분석가</div>", unsafe_allow_html=True)
        except FileNotFoundError:
             st.header("📝 차주 정보 입력")

        st.header("📝 차주 정보 입력")
        
        client_name = st.text_input("고객명", value="강성엽(실사업자)")
        
        # 숫자 입력 시 가독성을 위해 format 옵션 사용
        kb_price_input = st.number_input(
            "KB 시세 (원)", 
            value=1360000000, 
            step=1000000, 
            format="%d",
            help="KB부동산 일반평균가 기준"
        )
        
        existing_loan_input = st.number_input(
            "기존 대출 원금 (원)", 
            value=877000000, 
            step=1000000, 
            format="%d",
            help="기존 대출금액 합계"
        )
        
        st.subheader("⚙️ 대출 조건 설정")
        loan_type = st.radio("진행 방식", ["대환", "후순위(추가대출)"])
        credit_score = st.slider("신용점수 (NICE)", 600, 1000, 850)
        
        st.subheader("📍 물건지 상세")
        region_type = st.selectbox(
            "방공제 지역 기준", 
            ["서울", "과밀억제권역(경기/인천 등)", "광역시", "그외"],
            index=1 # 기본값 경기/인천
        )
        
        is_trust_mci = st.checkbox("신탁등기/MCI 사용 (방공제 면제)", value=True)
        
        bond_max_ratio = 1.2 # 기본값
        if loan_type == "후순위(추가대출)":
            bond_max_ratio = st.slider("기존 대출 설정비율 (%)", 110, 130, 120) / 100.0

        st.markdown("---")
        run_calc = st.button("🧮 핀모든 분석 시작", type="primary", use_container_width=True)

    # 메인 화면: 결과 출력
    if run_calc:
        calculator = MortgageCalculator()
        
        # 입력값 요약 표시 (컨테이너 활용)
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("KB 시세", f"{kb_price_input/100000000:,.1f}억")
            col2.metric("기존 대출", f"{existing_loan_input/100000000:,.2f}억")
            col3.metric("신용점수", f"{credit_score}점")
            col4.metric("진행 방식", loan_type)

        st.markdown("---")

        # 계산 실행
        df_result = calculator.calculate(
            kb_price=kb_price_input,
            existing_loan=existing_loan_input,
            loan_type=loan_type,
            region_type=region_type,
            is_trust_mci=is_trust_mci,
            credit_score=credit_score,
            bond_max_ratio=bond_max_ratio
        )

        if not df_result.empty
