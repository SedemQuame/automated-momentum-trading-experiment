import os
import logging
import asyncio
import argparse
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from deriv_api import DerivAPI
import csv

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove all handlers from the root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler("./src/logs/momentum-trader-log.txt")
c_handler.setLevel(logging.INFO)
f_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
f_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)


class MomentumTrader:
    """Class that implements momentum based strategy."""

    def __init__(
        self,
        api: DerivAPI,
        arguments: argparse.Namespace,
        contracts: List[Dict[str, Any]],
        lock: asyncio.Lock,
    ) -> None:
        self.position = 0
        self.momentum = 3
        self.bar_length = "1min"
        self.raw_data = pd.DataFrame()
        self.min_length = self.momentum + 1
        self.api = api
        self.arguments = arguments
        self.contracts = contracts
        self.data = pd.DataFrame()
        self.resample_rate = "120S"
        self.lock = lock

    async def buy_proposal(
        self, proposal: Dict[str, Any], price: int
    ) -> Dict[str, Any]:
        """Buys an options contract."""
        proposal_id = proposal.get("proposal").get("id")
        buy = await self.api.buy({"buy": proposal_id, "price": int(price)})
        return buy

    async def create_options_contract(
        self, contract_type: str, spot_price: float
    ) -> None:
        """Creates options contracts, on deriv.com"""
        proposal = await self.api.proposal(
            {
                "proposal": self.arguments.proposal_amount,
                "amount": self.arguments.amount,
                "barrier": "+0.10",
                "basis": "payout",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": self.arguments.duration,
                "duration_unit": "s",
                "symbol": self.arguments.symbol,
            }
        )
        if "error" not in proposal and "proposal" in proposal:
            # Place buy order
            async with self.lock:
                logger.info(f"Trading:- Buying {contract_type} contract @ {spot_price}")
                new_contract = await self.buy_proposal(proposal, spot_price)
                logger.info(new_contract)
                self.contracts.append(
                    {
                        "contract_id": new_contract["buy"]["contract_id"],
                        "pnl": 0,
                        "buy_price": new_contract["buy"]["buy_price"],
                        "possible_payout": new_contract["buy"]["payout"],
                        "start_time": new_contract["buy"]["start_time"],
                        "side": contract_type,
                        "status": "active",
                    }
                )

    def convert_timestamp(self, timestamp: float) -> str:
        """Converts timestam to human readable format."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

    def record_data(self, row):
        row = (row.iat[0, 0], row.iat[0, 1], row.iat[0, 2], row.iat[0, 3])
        filename = f"src/logs/{self.arguments.symbol}.csv"
        column_header = ("bid", "mid", "returns", "position")
        file_exists = os.path.isfile(filename)
        with open(filename, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(column_header)
            writer.writerow(row)

    async def trading_logic(self) -> None:
        """Trading logic, that implments the momentum trading strategy."""
        last_price = None
        prev_price = None
        account = await self.api.balance()
        curr_balance = intial_balance = account["balance"]["balance"]
        # Momentum strategy parameters
        while True and curr_balance >= intial_balance - 5:
            account = await self.api.balance()
            curr_balance = account["balance"]["balance"]
            logger.info(
                f"Current balance: {curr_balance} - Initial balance: {intial_balance}"
            )
            proposal = await self.api.proposal(
                {
                    "proposal": self.arguments.proposal_amount,
                    "amount": self.arguments.amount,
                    "barrier": "+0.1",
                    "basis": "payout",
                    "contract_type": "PUT",
                    "currency": "USD",
                    "duration": self.arguments.duration,
                    "duration_unit": "s",
                    "symbol": self.arguments.symbol,
                }
            )
            spot_price = proposal["proposal"]["spot"]
            spot_time = proposal["proposal"]["spot_time"]
            if curr_balance > intial_balance / 2 and last_price is not None:
                row = pd.DataFrame(
                    {"bid": spot_price},
                    index=[pd.Timestamp(self.convert_timestamp(spot_time))],
                )
                self.raw_data = self.raw_data._append(row)
                self.data = (
                    self.raw_data.resample(self.resample_rate).last().ffill().iloc[:-1]
                )
                self.data["mid"] = self.data.mean(axis=1)
                self.data["returns"] = np.log(
                    self.data["mid"] / self.data["mid"].shift(1)
                )
                self.data["position"] = np.sign(
                    self.data["returns"].rolling(self.momentum).mean()
                )
                logger.info(self.data)
                if len(self.data) > self.min_length:
                    self.min_length += 1
                    if self.data["position"].iloc[-1] == 1:
                        if self.position == 0 or self.position == -1:
                            await self.create_options_contract("CALL", spot_price)
                            # pause the momentum trader after a contract has been created.
                            # this is a precaution to prevent a BUY and SELL on the same
                            # asset class, within a short period of time.
                            await asyncio.sleep(self.arguments.duration * 0.5)
                        self.position = 1
                    elif self.data["position"].iloc[-1] == -1:
                        if self.position == 0 or self.position == 1:
                            await self.create_options_contract("PUT", spot_price)
                            # pause the momentum trader after a contract has been created.
                            # this is a precaution to prevent a BUY and SELL on the same
                            # asset class, within a short period of time.
                            await asyncio.sleep(self.arguments.duration * 0.5)
                        self.position = -1
            prev_price = last_price
            last_price = spot_price
            logger.info(f"Previous price: {prev_price} - Last price: {last_price}")
            if curr_balance > intial_balance + self.arguments.target:
                logger.info(f"Target amount reached.\nExiting script ...")
                exit()

            if self.data.size > 0:
                self.record_data(self.data.tail(1))
            await asyncio.sleep(5)
