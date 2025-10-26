# config.py
# Central place for thresholds, labels, and mappings the rest of the app uses.

# Which chains are cheap gas vs expensive gas.
CHEAP_GAS_CHAINS = ["Arbitrum", "Polygon", "Base", "Optimism", "Avalanche"]
EXPENSIVE_GAS_CHAINS = ["Ethereum"]

# Default minimum TVL to screen out ultra-tiny, sketchy pools.
MIN_TVL_DEFAULT = 250000  # $250k

# If a pool on Ethereum has less than this TVL, we consider it a red flag,
# because gas is high and exit risk is higher.
RED_FLAG_TVL_ETH_THRESHOLD = 250000  # $250k

# Mapping of protocol/project names (from DeFiLlama "project") to human safety notes.
# We will expand this over time.
PROTOCOL_SAFETY = {
    "uniswap-v3": "Audited / Clean",
    "curve": "Audited / Clean",
    "balancer-v2": "Audited / Clean",
    # add more known names as you go
    # unknown ones will default to "Unknown"
}
