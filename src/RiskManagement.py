import logging
import pprint
import asyncio
import argparse
from typing import List, Dict, Any
from deriv_api import DerivAPI
import deriv_api.errors
import datetime

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove all handlers from the root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create handlers
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler("./src/logs/risk-management-log.txt")
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


class RiskManagement:
    def __init__(
        self,
        api: DerivAPI,
        contracts: List[Dict[str, Any]],
        arguments: argparse.Namespace,
        lock: asyncio.Lock,
    ) -> None:
        self.api = api
        self.contracts = contracts
        self.arguments = arguments
        self.lock = lock

    def get_seconds_left_to_expiry(self, date_start, date_expiry):
        now = datetime.datetime.now()
        difference = date_expiry - now
        return difference.total_seconds()

    async def risk_management_logic(self) -> None:
        """Risk management logic, using a scalping approach."""
        while True:
            logger.info(f"Current number of contracts: {len(self.contracts)}")
            # Use pformat to convert to string for logging
            logger.info(pprint.pformat(self.contracts))

            # Check PNL on all active contracts
            async with self.lock:
                for index, contract_info in enumerate(self.contracts):
                    if contract_info["status"] == "active":
                        try:
                            # Retrieve contract information for the current contract
                            contract_info = await self.api.proposal_open_contract(
                                {
                                    "proposal_open_contract": 1,
                                    "contract_id": contract_info["contract_id"],
                                }
                            )
                            # Use pformat to convert to string for logging
                            logger.info("\n" + pprint.pformat(contract_info))

                            pnl = contract_info["proposal_open_contract"]["profit"]
                            contract_id = contract_info["proposal_open_contract"][
                                "contract_id"
                            ]

                            req_id = contract_info["req_id"]
                            sell_contract = {
                                "price": 0,
                                "req_id": req_id,
                                "sell": contract_id,
                            }
                            # calculate the number of seconds left for the contract to expire
                            date_start = datetime.datetime.fromtimestamp(
                                contract_info["proposal_open_contract"]["date_start"]
                            )
                            date_expiry = datetime.datetime.fromtimestamp(
                                contract_info["proposal_open_contract"]["date_expiry"]
                            )
                            seconds_left_till_contract_expiry = (
                                self.get_seconds_left_to_expiry(date_start, date_expiry)
                            )
                            logger.info(
                                f"Seconds left till contract expires: {seconds_left_till_contract_expiry} out of {self.arguments.duration * 0.8}"
                            )
                            # Exit trade if momentum of contract price has approached the calculated_loss
                            if pnl >= 0.01 * self.arguments.amount or (
                                (
                                    seconds_left_till_contract_expiry
                                    < self.arguments.duration * 0.8
                                )
                                and pnl <= -0.01 * self.arguments.amount
                            ):
                                # if (pnl >= 0.15 * (self.arguments.amount / 2)) or (pnl <= -0.25 * (self.arguments.amount / 2)):
                                logger.info(
                                    f"Risk management: Sell the contract {contract_id} when pnl is {pnl}."
                                )
                                await self.api.sell(sell_contract)
                                # Remove the sold contract from the contracts deque
                                del self.contracts[index]
                        except deriv_api.errors.ResponseError as e:
                            logger.error("Error occurred:", exc_info=True)
                        except Exception as e:
                            logger.error("Error occurred:", exc_info=True)
                    else:
                        self.contracts.remove(contract_info)
            await asyncio.sleep(5)
