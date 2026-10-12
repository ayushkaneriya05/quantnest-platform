class InstrumentResolver:
    """Resolves the actual execution instrument from a signal instrument + route config."""

    @staticmethod
    def validate_strategy_for_first_release(strategy):
        """Validate that every watchlist instrument uses direct routing."""
        for watch in strategy.watchlist_instruments.all():
            for route in watch.execution_routes.all():
                if route.route_type != "DIRECT":
                    raise ValueError(
                        f"Routing type '{route.route_type}' is disabled. Only DIRECT routing is supported."
                    )
        return True


    @staticmethod
    def execution_instrument_ids(session):
        """Return the deployed watchlist instrument IDs for the active session.
        Execution must always use the strategy version pinned to the active session.
        The config snapshot contains the instruments selected for this deployment.
        """
        candidate = session
        if hasattr(candidate, 'allocation') and candidate.allocation is not None:
            candidate = candidate.allocation
        if not hasattr(candidate, 'deployed_version') or candidate.deployed_version is None:
            raise ValueError("Session has no deployed strategy version configured for execution.")

        config = candidate.deployed_version.config_snapshot or {}
        direct_ids = [item['instrument_id'] for item in config['watchlist_instruments']]
        if not direct_ids:
            raise ValueError("Deployed strategy snapshot has no watchlist instruments for execution.")
        return sorted({int(item) for item in direct_ids if item is not None})

    
    @staticmethod
    def resolve(watchlist_instrument, signal_side, routes_data=None):
        """
        Returns a list of (execution_instrument, execution_side, route_sizing_dict).
        If no routes → returns the original instrument and side unchanged.
        
        Args:
            watchlist_instrument: WatchlistInstrument object or dict
            signal_side: Trading side (BUY/SELL)
            routes_data: Pre-loaded execution routes (to avoid DB query)
        """
        # Use routes_data if provided, otherwise query DB
        if routes_data is not None:
            routes = routes_data  # Use pre-loaded data
        else:
            # Model-backed callers provide execution routes through the relation
            if hasattr(watchlist_instrument, 'execution_routes'):
                routes = watchlist_instrument.execution_routes.all()
            else:
                routes = []
        
        if not routes or (hasattr(routes, 'exists') and not routes.exists()):
            # DIRECT route - return base instrument
            if isinstance(watchlist_instrument, dict):
                # Handle dict format from config
                inst_id = watchlist_instrument.get('instrument_id')
                # Return instrument ID for deferred resolution
                return [(inst_id, signal_side, None)]
            else:
                return [(watchlist_instrument.instrument, signal_side, None)]
            
        results = []
        for route in routes:
            # Handle both model objects and dict format
            if isinstance(route, dict):
                route_type = route.get('route_type')
                sizing = dict(route) if route.get('override_sizing', False) else None
            else:
                route_type = route.route_type
                sizing = route.get_sizing_dict()

            if route_type != "DIRECT":
                raise ValueError(
                    f"Unsupported routing type '{route_type}'. Only DIRECT routing is enabled."
                )
            
            def _enforce(sz, inst):
                if sz and sz.get("sizing_method") == "FIXED" and sz.get("fixed_quantity"):
                    lot = getattr(inst, 'lot_size', 1) or 1
                    sz["fixed_quantity"] = max(lot, round(sz["fixed_quantity"] / lot) * lot)
                return sz

            if isinstance(watchlist_instrument, dict):
                inst_id = watchlist_instrument.get('instrument_id')
                results.append((inst_id, signal_side, _enforce(sizing, watchlist_instrument)))
            else:
                results.append((watchlist_instrument.instrument, signal_side, _enforce(sizing, watchlist_instrument.instrument)))

        return results
