"""
A trading bot, that buys and sells options contracts from the deriv platform.
Using a momentum trading strategy and a scalping risk management approach.
"""
import os
import logging
import asyncio
import argparse
from typing import List, Dict, Any
from deriv_api import DerivAPI
from dotenv import load_dotenv
from MomentumTrader import MomentumTrader
from RiskManagement import RiskManagement

load_dotenv()


async def run_trading_logic(
    api: DerivAPI,
    contracts: List[Dict[str, Any]],
    arguments: argparse.Namespace,
    lock: asyncio.Lock,
) -> None:
    """Run the trading logic, which uses the momentum trading strategy."""
    trader = MomentumTrader(api, arguments, contracts, lock)
    await trader.trading_logic()


async def run_risk_management_logic(
    api: DerivAPI,
    contracts: List[Dict[str, Any]],
    arguments: argparse.Namespace,
    lock: asyncio.Lock,
) -> None:
    """Runs the risk Management logic, which uses a scalping strategy."""
    risk = RiskManagement(api, contracts, arguments, lock)
    await risk.risk_management_logic()


async def run_tasks(api: DerivAPI, arguments: argparse.Namespace) -> None:
    """Runs the logic for risk management and trading asynchronously."""
    contracts = []
    lock = asyncio.Lock()
    risk_task = asyncio.create_task(
        run_risk_management_logic(api, contracts, arguments, lock)
    )
    trading_task = asyncio.create_task(
        run_trading_logic(api, contracts, arguments, lock)
    )
    await asyncio.gather(trading_task, risk_task)


async def main() -> None:
    """Deriv API endpoint and app_id"""
    api = DerivAPI(app_id=os.getenv("APP_ID"))
    await api.authorize(os.getenv("DERIV_API"))
    await run_tasks(api, args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--symbol",
        default="R_100",
        choices=[
            "1HZ10V",
            "R_10",
            "1HZ25V",
            "R_25",
            "1HZ50V",
            "R_50",
            "1HZ75V",
            "R_75",
            "1HZ100V",
            "R_100",
            "1HZ150V",
            "1HZ250V",
            "OTC_DJI",
        ],
    )
    parser.add_argument("-p", "--proposal_amount", default=1, type=int)
    # the default amount to by a proposal at.
    parser.add_argument("-a", "--amount", default=10, type=int)
    # the default run time for a contract should be 1 full day (intraday trading)
    parser.add_argument("-d", "--duration", default=3600, type=int)
    # target to take profits at.
    parser.add_argument("-t", "--target", default=4, type=int)
    args = parser.parse_args()
    asyncio.run(main())
