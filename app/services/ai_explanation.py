import os
import re
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Khởi tạo Logger theo dõi quá trình sinh bài viết và bắt lỗi Guardrails
logger = logging.getLogger("cluster4_ai_explanation")
logger.setLevel(logging.INFO)

# Kiểm tra thư viện Google Gemini API
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


# =====================================================================
# MODULE 4.1: PROMPT BUILDER & LLM WRAPPER (Nhóm G5 - SV 1)
# =====================================================================
class LLMClientWrapper:
    """
    Module 4.1: Quản lý kết nối LLM với cơ chế Tự động dò tìm Model khả dụng (Auto-Discovery).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        
        if HAS_GEMINI and self.api_key:
            genai.configure(api_key=self.api_key)
            self._is_active = True
        else:
            self._is_active = False
            logger.warning("Gemini API Key chưa được cấu hình hoặc thiếu thư viện google-generativeai.")

    def _get_available_model_names(self) -> List[str]:
        """
        Dò tìm danh sách các model đang hoạt động và hỗ trợ hàm generateContent trên API Key hiện tại.
        Đồng thời loại bỏ các model chuyên dụng cho âm thanh (TTS).
        """
        discovered_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    # Bỏ qua các model bản Text-to-Speech (TTS) chỉ hỗ trợ Audio
                    if "tts" not in m.name.lower():
                        discovered_models.append(m.name)
        except Exception as e:
            logger.warning(f"[Module 4.1] Không thể lấy danh sách Model tự động: {str(e)}")

        # Nếu tìm thấy model từ API thì ưu tiên dùng, nếu không sẽ dùng danh sách dự phòng chuẩn
        if discovered_models:
            return discovered_models

        return [
            "gemini-2.5-flash",
            "models/gemini-2.5-flash",
            "gemini-2.0-flash",
            "models/gemini-2.0-flash",
            "gemini-1.5-flash",
            "models/gemini-1.5-flash"
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True
    )
    def generate_text_with_retry(self, prompt: str, system_instruction: str) -> str:
        """
        Gọi API sinh văn bản với cơ chế Retry tự động và tự dò chọn Model chạy được.
        """
        if not self._is_active:
            raise RuntimeError("Gemini API Client chưa sẵn sàng.")

        candidate_models = self._get_available_model_names()
        last_exception = None

        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.15,
                        "max_output_tokens": 4096,  # Nâng token để AI viết trọn vẹn bài
                        "top_p": 0.8
                    }
                )

                if response and response.text:
                    logger.info(f"[Module 4.1 Success] Kết nối thành công với Gemini Model: {model_name}")
                    return response.text.strip()

            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                
                # SỬA ĐỔI: Bỏ qua không chỉ lỗi 404 mà cả lỗi 400 / không hỗ trợ modalities / TTS để chuyển sang model tiếp theo
                if "404" in err_str or "not found" in err_str or "400" in err_str or "modalities" in err_str or "tts" in err_str:
                    logger.warning(f"[Module 4.1] Model {model_name} không khả dụng hoặc không hỗ trợ văn bản ({str(e)}), thử model tiếp theo...")
                    continue
                else:
                    raise e

        raise last_exception or ValueError("Không tìm thấy mô hình Gemini nào hỗ trợ generateContent.")
    
# =====================================================================
# MODULE 4.2: STRUCTURED PROMPT & CONTEXT BUILDER (Nhóm G5 - SV 2)
# =====================================================================
class PromptBuilder:
    """
    Module 4.2: Trích xuất, nén và cấu trúc dữ liệu JSON từ Cluster 2 & 3
    thành Prompt tối ưu ngữ cảnh cho AI.
    """

    @staticmethod
    def get_system_instruction() -> str:
        return (
            "Bạn là 'AI Financial Portfolio Advisor' - Cố vấn Đầu tư Tài chính Cao cấp.\n"
            "Nhiệm vụ của bạn là giải thích lý do phân bổ vốn cho người dùng dựa HOÀN TOÀN vào dữ liệu JSON được cấp.\n\n"
            "QUY TẮC BẮT BUỘC KHÔNG ĐƯỢC VI PHẠM:\n"
            "1. KHÔNG TỰ BỊA ĐẶT HOẶC SUY DOÁN: Tuyệt đối không thay đổi bất kỳ con số nào (số tiền, tỷ lệ %, RSI, MACD, Score).\n"
            "2. CHỈ DÙNG MÃ CÓ TRONG DATA: Không đề xuất hoặc nhắc tới các mã cổ phiếu ngoài danh mục JSON.\n"
            "3. ĐỊNH DẠNG BÀI VIẾT:\n"
            "   - Tiêu đề: Tóm tắt tổng vốn đầu tư.\n"
            "   - Mục 1: Bảng phân bổ & Điểm số cổ phiếu (Nêu rõ $ và %).\n"
            "   - Mục 2: Giải thích lý do phân bổ từng mã (Trích dẫn chỉ số RSI, MACD, Sharpe, Beta, Volatility).\n"
            "   - Mục 3: Cảnh báo rủi ro & Lời khuyên đa dạng hóa vốn (Nhấn mạnh giới hạn Cap 35%/mã nếu có mã đạt trần).\n"
            "4. NGÔN NGỮ: Tiếng Việt chuyên nghiệp, ngắn gọn, súc tích (dưới 400 từ)."
        )

    @classmethod
    def build_user_prompt(cls, portfolio_data: Dict[str, Any], analytics_data: Dict[str, Any]) -> str:
        scores = portfolio_data.get("scores", {})
        allocation = portfolio_data.get("allocation", {})
        weights = allocation.get("weights_percent", {})
        amounts = allocation.get("amount_allocated", {})
        total_inv = allocation.get("total_investment", 10000.0)
        applied_cap = allocation.get("applied_cap_percent", 35.0)

        stocks_context = {}
        for sym, score in scores.items():
            analytics = analytics_data.get(sym, {})
            perf = analytics.get("performance", {})
            trend = analytics.get("trend_indicators", {})
            risk = analytics.get("risk_metrics", {})
            macd_info = trend.get("macd", {})

            stocks_context[sym] = {
                "dinh_gia": {
                    "stock_score": score,
                    "ty_le_phan_bo_pct": weights.get(sym, 0.0),
                    "so_tien_phan_bo_usd": amounts.get(sym, 0.0)
                },
                "chi_so_ky_thuat": {
                    "total_return_1y": f"{perf.get('total_return_1y', 0)*100:.2f}%",
                    "rsi_14": trend.get("rsi_14"),
                    "rsi_status": trend.get("rsi_status"),
                    "macd_bullish": macd_info.get("is_bullish", False),
                    "sma_20": trend.get("sma_20"),
                    "sma_50": trend.get("sma_50")
                },
                "chi_so_rui_ro": {
                    "sharpe_ratio": risk.get("sharpe_ratio"),
                    "annual_volatility": f"{risk.get('annual_volatility', 0)*100:.2f}%",
                    "max_drawdown": f"{risk.get('max_drawdown', 0)*100:.2f}%",
                    "beta": risk.get("beta")
                }
            }

        input_payload = {
            "tong_von_dau_tu_usd": total_inv,
            "gioi_han_cap_moi_ma_pct": applied_cap,
            "danh_sach_co_phieu": stocks_context
        }

        return f"""
            Dưới đây là dữ liệu tài chính chính xác từ hệ thống phân tích. Hãy viết bài giải thích chi tiết theo đúng Quy tắc System Instruction:

            ```json
            {json.dumps(input_payload, ensure_ascii=False, indent=2)}
        """

# =====================================================================
# MODULE 4.3: RESPONSE VALIDATION & GUARDRAILS (Nhóm G5 - SV 3)
# =====================================================================
class GuardrailValidator:
    SAFE_FINANCIAL_TOKENS = {
        "USD", "VND", "RSI", "MACD", "SMA", "EMA", "BETA", "CAP", "SCORE", "JSON", "AI", "API",
        "NAV", "PE", "PB", "EPS", "ROE", "ROA", "CAGR", "HOLT",
        "MUA", "BAN", "BÁN", "NAM", "NẮM", "GIU", "GIỮ", 
        "TRUNG", "BÌNH", "LỆNH", "GIAO", "DỊCH", "DANH", "MỤC", "TỔNG",
        "BUY", "SELL", "HOLD", "HIGH", "LOW", "NEUTRAL", "BULLISH", "BEARISH", "OVERSOLD", "OVERBOUGHT"
    }
    
    @classmethod
    def validate(cls, ai_response_text: str, portfolio_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        allocations = portfolio_data.get("allocation", {}).get("amount_allocated", {})
        valid_symbols = set(allocations.keys())

        raw_found_tokens = set(re.findall(r'\b[A-Z]{2,5}\b', ai_response_text))
        suspicious_symbols = raw_found_tokens - cls.SAFE_FINANCIAL_TOKENS - valid_symbols

        if suspicious_symbols:
            errors.append(f"Phát hiện mã cổ phiếu lạ/không nằm trong danh mục: {suspicious_symbols}")

        total_inv = portfolio_data.get("allocation", {}).get("total_investment", 0.0)
        total_inv_int = int(total_inv)
        
        expected_patterns = [
            f"{total_inv_int}",
            f"{total_inv_int:,}",
            f"${total_inv_int:,}"
        ]
        
        has_amount_match = any(pattern in ai_response_text for pattern in expected_patterns)
        if not has_amount_match and total_inv > 0:
            errors.append(f"Không tìm thấy xác nhận tổng số tiền ${total_inv_int:,} trong văn bản giải thích.")

        if len(ai_response_text) < 100:
            errors.append("Văn bản phản hồi quá ngắn hoặc không đủ chất lượng.")

        negative_keywords = ["xin lỗi", "không thể thực hiện", "không có dữ liệu"]
        if any(kw in ai_response_text.lower() for kw in negative_keywords) and len(valid_symbols) > 0:
            errors.append("Phát hiện phản hồi từ chối sinh nội dung từ AI Model.")

        is_valid = len(errors) == 0
        return is_valid, errors

# =====================================================================
# MAIN SERVICE: CLUSTER 4 INTEGRATION SERVICE
# =====================================================================
class AIExplanationService:
    @classmethod
    def generate_explanation(
        cls, 
        portfolio_data: Dict[str, Any], 
        analytics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        system_instruction = PromptBuilder.get_system_instruction()
        user_prompt = PromptBuilder.build_user_prompt(portfolio_data, analytics_data)

        llm_wrapper = LLMClientWrapper()

        try:
            raw_ai_text = llm_wrapper.generate_text_with_retry(
                prompt=user_prompt, 
                system_instruction=system_instruction
            )

            is_valid, validation_errors = GuardrailValidator.validate(raw_ai_text, portfolio_data)

            if is_valid:
                logger.info("[Cluster 4 Success] AI sinh văn bản thành công và đã vượt qua Guardrails Validation.")
                return {
                    "explanation_markdown": raw_ai_text,
                    "is_ai_generated": True,
                    "guardrail_passed": True,
                    "validation_errors": []
                }
            else:
                logger.warning(f"[Cluster 4 Guardrail Violation] Vi phạm: {validation_errors}. Chuyển sang Fallback.")
                fallback_text = cls._generate_deterministic_fallback(portfolio_data, analytics_data)
                return {
                    "explanation_markdown": fallback_text,
                    "is_ai_generated": False,
                    "guardrail_passed": False,
                    "validation_errors": validation_errors
                }

        except Exception as e:
            logger.error(f"[Cluster 4 Fallback Triggered] Lỗi kết nối AI: {str(e)}")
            fallback_text = cls._generate_deterministic_fallback(portfolio_data, analytics_data)
            return {
                "explanation_markdown": fallback_text,
                "is_ai_generated": False,
                "guardrail_passed": False,
                "validation_errors": [f"System/Network Error: {str(e)}"]
            }

    @staticmethod
    def _generate_deterministic_fallback(portfolio_data: Dict[str, Any], analytics_data: Dict[str, Any]) -> str:
        allocation = portfolio_data.get("allocation", {})
        scores = portfolio_data.get("scores", {})
        total_inv = allocation.get("total_investment", 10000.0)
        weights = allocation.get("weights_percent", {})
        amounts = allocation.get("amount_allocated", {})

        details_list = []
        for sym, score in scores.items():
            pct = weights.get(sym, 0.0)
            amt = amounts.get(sym, 0.0)
            analytics = analytics_data.get(sym, {})
            rsi = analytics.get("trend_indicators", {}).get("rsi_14", "N/A")
            is_bullish = analytics.get("trend_indicators", {}).get("macd", {}).get("is_bullish", False)
            macd_str = "Tín hiệu Tăng (Bullish)" if is_bullish else "Tín hiệu Giảm/Đi ngang"

            details_list.append(
                f"* **{sym}** (Điểm: **{score}/100**):\n"
                f"  - Tỷ lệ phân bổ: **{pct}%** (Tương đương **${amt:,.2f}**)\n"
                f"  - Chỉ số RSI(14): **{rsi}** | MACD: **{macd_str}**"
            )

        details_str = "\n".join(details_list)

        return f"""### 📊 Tóm tắt Phân bổ Danh mục Đầu tư (Tổng vốn: ${total_inv:,.2f})\n\n{details_str}"""