"""
Views for the strategies app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig, ReEntryRule
from .serializers import (
    StrategyListSerializer, StrategyDetailSerializer, StrategyCreateSerializer,
    StrategyVersionSerializer, StrategyTagSerializer,
    EntryOrderConfigSerializer, ExitOrderConfigSerializer, ReEntryRuleSerializer
)
from .services import StrategySnapshotService


class StrategyTagViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy tags."""
    queryset = StrategyTag.objects.all()
    serializer_class = StrategyTagSerializer
    permission_classes = [permissions.IsAuthenticated]


class StrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for CRUD operations on strategies."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter strategies by current user."""
        return Strategy.objects.filter(user=self.request.user).select_related(
            'user'
        ).prefetch_related('tags')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StrategyListSerializer
        elif self.action == 'create':
            return StrategyCreateSerializer
        return StrategyDetailSerializer
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone an existing strategy."""
        original = self.get_object()
        
        # Create new strategy with copied data
        new_strategy = Strategy.objects.create(
            user=request.user,
            name=f"{original.name} (Copy)",
            description=original.description,
            strategy_type=original.strategy_type,
            market_type=original.market_type,
            exchange=original.exchange,
            instrument_type=original.instrument_type,
            visibility='PRIVATE',
            status='DRAFT',
        )
        new_strategy.tags.set(original.tags.all())
        
        # Clone configs
        if hasattr(original, 'entry_order_config'):
            config = original.entry_order_config
            EntryOrderConfig.objects.update_or_create(
                strategy=new_strategy,
                defaults={
                    'order_type': config.order_type,
                    'entry_price_logic': config.entry_price_logic,
                    'price_offset': config.price_offset,
                }
            )
        

        # Clone exit config
        if hasattr(original, 'exit_order_config'):
            config = original.exit_order_config
            ExitOrderConfig.objects.create(
                strategy=new_strategy,
                stop_loss_group_operator=config.stop_loss_group_operator,
                target_group_operator=config.target_group_operator
            )

        serializer = StrategyDetailSerializer(new_strategy, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a draft or paused strategy."""
        strategy = self.get_object()
        if strategy.status in ('DRAFT', 'PAUSED'):
            strategy.status = 'ACTIVE'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an active strategy."""
        strategy = self.get_object()
        if strategy.status == 'ACTIVE':
            strategy.status = 'PAUSED'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='create-version')
    def create_version(self, request, pk=None):
        """Create a new version snapshot."""
        strategy = self.get_object()
        notes = request.data.get('notes', '')
        
        try:
            version = StrategySnapshotService.create_snapshot(
                strategy, 
                user=request.user, 
                change_notes=notes
            )
            serializer = StrategyVersionSerializer(version)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """Rollback strategy to a specific version."""
        strategy = self.get_object()
        version_id = request.data.get('version_id')
        
        if not version_id:
            return Response({'error': 'version_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            strategy = StrategySnapshotService.restore_version(strategy, version_id)
            serializer = StrategyDetailSerializer(strategy, context={'request': request})
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get history of versions."""
        strategy = self.get_object()
        versions = strategy.versions.all()
        serializer = StrategyVersionSerializer(versions, many=True)
        return Response(serializer.data)

    def get_object(self):
        """
        Override get_object to ensure config objects exist.
        This handles cases where strategies were created before signals were added.
        """
        obj = super().get_object()
        
        # Ensure EntryOrderConfig exists
        if not hasattr(obj, 'entry_order_config'):
            EntryOrderConfig.objects.create(strategy=obj)
            
        # Ensure ReEntryRule exists
        if not hasattr(obj, 'reentry_rule'):
            ReEntryRule.objects.create(strategy=obj)

        # Ensure ExitOrderConfig exists
        if not hasattr(obj, 'exit_order_config'):
            ExitOrderConfig.objects.create(strategy=obj)
            
        # Refresh to get the new reverse relationships
        obj.refresh_from_db()
        return obj
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a strategy."""
        strategy = self.get_object()
        strategy.status = 'ARCHIVED'
        strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a strategy back to draft."""
        strategy = self.get_object()
        if strategy.status == 'ARCHIVED':
            strategy.status = 'DRAFT'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get version history for a strategy."""
        strategy = self.get_object()
        versions = strategy.versions.all()
        serializer = StrategyVersionSerializer(versions, many=True)
        return Response(serializer.data)


class EntryOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for entry order configuration."""
    serializer_class = EntryOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EntryOrderConfig.objects.filter(strategy__user=self.request.user)


class ReEntryRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for re-entry rules."""
    serializer_class = ReEntryRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ReEntryRule.objects.filter(strategy__user=self.request.user)


class ExitOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for exit order configuration."""
    serializer_class = ExitOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ExitOrderConfig.objects.filter(strategy__user=self.request.user)
