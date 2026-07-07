from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from locust_global_market_system import DataSource, MarketSnapshot, MarketType


@dataclass(frozen=True)
class AShareQuery:
    symbol: str
    set_code: int
    trend: float
    volatility: float


@dataclass(frozen=True)
class FutuQuery:
    symbol: str
    market_type: MarketType
    trend: float
    volatility: float


class ConnectorError(RuntimeError):
    pass


class AKShareMarketConnector:
    def __init__(
        self,
        spot_fetcher: Callable[[], Any] | None = None,
        eastmoney_connector: "EastmoneyFlowConnector | None" = None,
    ) -> None:
        self.spot_fetcher = spot_fetcher
        self.eastmoney_connector = eastmoney_connector or EastmoneyFlowConnector()

    def fetch_snapshot(self, query: AShareQuery) -> MarketSnapshot:
        try:
            payload = self._fetch_spot_payload()
        except ConnectorError:
            payload = _fetch_sina_quote_payload((query.symbol,))
        return self._snapshot_from_payload(payload, query)

    def fetch_snapshots(self, queries: tuple[AShareQuery, ...]) -> tuple[MarketSnapshot, ...]:
        try:
            payload = self._fetch_spot_payload()
        except ConnectorError:
            payload = _fetch_sina_quote_payload(tuple(query.symbol for query in queries))
        return tuple(self._snapshot_from_payload(payload, query) for query in queries)

    def fetch_snapshot_map(
        self, queries: tuple[AShareQuery, ...]
    ) -> tuple[dict[str, MarketSnapshot], dict[str, str]]:
        try:
            payload = self._fetch_spot_payload()
        except ConnectorError:
            payload = _fetch_sina_quote_payload(tuple(query.symbol for query in queries))
        snapshots: dict[str, MarketSnapshot] = {}
        errors: dict[str, str] = {}
        for query in queries:
            try:
                snapshots[query.symbol] = self._snapshot_from_payload(payload, query)
            except ConnectorError as exc:
                errors[query.symbol] = str(exc)
        return snapshots, errors

    def _snapshot_from_payload(self, payload: Any, query: AShareQuery) -> MarketSnapshot:
        row = _find_symbol_row(payload, query.symbol)
        price = _first_number(row, ("最新价", "price", "last_price", "trade", "最新", "现价", "收盘价"))
        volume = _first_number(row, ("成交量", "volume", "vol", "总手"))
        if price is None:
            raise ConnectorError("AKShare 未返回可用A股实时价格。")
        return MarketSnapshot(
            symbol=query.symbol,
            market_type=MarketType.A_SHARE,
            source=DataSource.AKSHARE,
            price=price,
            volume=volume or 0.0,
            trend=query.trend,
            volatility=query.volatility,
            locust_score=None,
            risk_score=None,
        )

    def fetch_strategy_snapshot(self, query: AShareQuery, fund_flow_period: int = 20) -> MarketSnapshot:
        snapshot = self.fetch_snapshot(query)
        locust_score = self.eastmoney_connector.fetch_fund_flow_score(query.symbol, period=fund_flow_period)
        return MarketSnapshot(
            symbol=snapshot.symbol,
            market_type=snapshot.market_type,
            source=snapshot.source,
            price=snapshot.price,
            volume=snapshot.volume,
            trend=snapshot.trend,
            volatility=snapshot.volatility,
            locust_score=locust_score,
            risk_score=snapshot.volatility,
        )

    def _fetch_spot_payload(self) -> Any:
        if self.spot_fetcher is not None:
            return self.spot_fetcher()
        try:
            import akshare as ak
        except Exception as exc:
            raise ConnectorError("akshare 未安装或不可导入。") from exc

        sina_errors: list[str] = []
        for _ in range(3):
            try:
                return ak.stock_zh_a_spot()
            except Exception as exc:
                sina_errors.append(str(exc))
                time.sleep(1)

        try:
            return ak.stock_zh_a_spot_em()
        except Exception as em_exc:
            raise ConnectorError(
                "AKShare A股实时行情调用失败："
                + " | ".join(sina_errors)
                + f"; 东方财富备用接口失败：{em_exc}"
            ) from em_exc


class EastmoneyFlowConnector:
    def __init__(self, flow_fetcher: Callable[[str, int], Any] | None = None) -> None:
        self.flow_fetcher = flow_fetcher

    def fetch_fund_flow_score(self, symbol: str, period: int = 20) -> float:
        payload = self._fetch_flow_payload(symbol, period)
        net_flow = _extract_number(payload, ("主力净流入", "主力净流入-净额", "netInflow", "mainNetInflow", "资金净流入"))
        if net_flow is None:
            return 50.0
        if net_flow > 0:
            return min(100.0, 60.0 + net_flow / 10_000_000)
        return max(0.0, 50.0 + net_flow / 10_000_000)

    def _fetch_flow_payload(self, symbol: str, period: int) -> Any:
        if self.flow_fetcher is not None:
            return self.flow_fetcher(symbol, period)
        try:
            import akshare as ak
        except Exception as exc:
            raise ConnectorError("akshare 未安装，无法调用 Eastmoney 资金流接口。") from exc
        code = _normalize_a_share_code(symbol)
        try:
            return ak.stock_individual_fund_flow(stock=code, market=_eastmoney_market(symbol))
        except Exception as exc:
            raise ConnectorError("Eastmoney 资金流接口调用失败。") from exc


class FutuOpenDConnector:
    def __init__(self, host: str = "127.0.0.1", port: int = 11111) -> None:
        self.host = host
        self.port = port

    def fetch_snapshot(self, query: FutuQuery) -> MarketSnapshot:
        try:
            import futu as ft
        except Exception as exc:
            raise ConnectorError("futu-api 未安装或不可导入。") from exc

        quote_ctx = ft.OpenQuoteContext(host=self.host, port=self.port)
        try:
            ret, data = quote_ctx.get_market_snapshot([query.symbol])
            if ret != ft.RET_OK:
                raise ConnectorError(f"Futu OpenD 返回错误：{data}")
            row = data.iloc[0].to_dict()
        finally:
            quote_ctx.close()

        price = _first_number(row, ("last_price", "price", "cur_price", "close_price"))
        volume = _first_number(row, ("volume", "turnover", "volume_sell", "volume_buy"))
        if price is None:
            raise ConnectorError("Futu OpenD 未返回可用价格。")
        return MarketSnapshot(
            symbol=query.symbol,
            market_type=query.market_type,
            source=DataSource.FUTU_OPENAPI,
            price=price,
            volume=volume or 0.0,
            trend=query.trend,
            volatility=query.volatility,
        )


def _find_symbol_row(payload: Any, symbol: str) -> dict[str, Any]:
    rows = _payload_rows(payload)
    code = _normalize_a_share_code(symbol)
    for row in rows:
        row_code = str(row.get("代码") or row.get("code") or row.get("symbol") or "")
        if _normalize_a_share_code(row_code) == code:
            return row
    if len(rows) == 1:
        return rows[0]
    raise ConnectorError(f"AKShare 未返回 {symbol} 的实时行情。")


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    if hasattr(payload, "to_dict"):
        try:
            records = payload.to_dict("records")
            if isinstance(records, list):
                return [dict(item) for item in records]
        except TypeError:
            pass
    if isinstance(payload, dict):
        if "data" in payload:
            return _payload_rows(payload["data"])
        return [payload]
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    raise ConnectorError("数据源未返回可识别的表格结构。")


def _extract_number(payload: Any, names: tuple[str, ...]) -> float | None:
    if isinstance(payload, dict):
        direct = _first_number(payload, names)
        if direct is not None:
            return direct
        for value in payload.values():
            found = _extract_number(value, names)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_number(item, names)
            if found is not None:
                return found
    elif hasattr(payload, "to_dict"):
        return _extract_number(_payload_rows(payload), names)
    return None


def _first_number(mapping: dict[str, Any], names: tuple[str, ...]) -> float | None:
    normalized = {str(key).lower(): value for key, value in mapping.items()}
    for name in names:
        if name in mapping:
            return _to_float(mapping[name])
        value = normalized.get(name.lower())
        if value is not None:
            return _to_float(value)
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("%", "").strip()
        if cleaned in {"", "--", "-"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_a_share_code(symbol: str) -> str:
    code = symbol.split(".")[0].lower()
    return code.replace("sh", "").replace("sz", "")


def _eastmoney_market(symbol: str) -> str:
    return "sh" if symbol.endswith(".SH") or symbol.startswith("6") else "sz"


def _fetch_sina_quote_payload(symbols: tuple[str, ...]) -> list[dict[str, Any]]:
    if not symbols:
        return []
    sina_symbols = ",".join(_sina_symbol(symbol) for symbol in symbols)
    url = f"https://hq.sinajs.cn/list={sina_symbols}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn/",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("gbk", errors="ignore")
    except Exception as exc:
        raise ConnectorError("Sina A股逐只行情兜底接口调用失败。") from exc

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if '="' not in line:
            continue
        left, payload = line.split('="', 1)
        symbol = left.rsplit("_", 1)[-1]
        fields = payload.rstrip('";').split(",")
        if len(fields) < 10 or not fields[0]:
            continue
        rows.append(
            {
                "代码": symbol,
                "名称": fields[0],
                "最新价": fields[3],
                "成交量": fields[8],
                "成交额": fields[9],
                "时间戳": fields[31] if len(fields) > 31 else "",
            }
        )
    if not rows:
        raise ConnectorError("Sina A股逐只行情未返回可用数据。")
    return rows


def _sina_symbol(symbol: str) -> str:
    code = _normalize_a_share_code(symbol)
    upper = symbol.upper()
    if upper.endswith(".SH") or code.startswith("6"):
        return f"sh{code}"
    if upper.endswith(".BJ") or code.startswith(("8", "9")):
        return f"bj{code}"
    return f"sz{code}"
