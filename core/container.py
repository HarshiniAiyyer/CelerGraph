# container.py
"""Dependency injection container for GraphRAG services.

Implements Inversion of Control (IoC) pattern following the
Dependency Inversion Principle. Manages service lifecycle and
provides loose coupling between components.
"""

from typing import Dict, Type, Any, Optional, Callable
from dataclasses import dataclass

from core.interfaces import (
    ServiceContainer
)
from config.settings import GraphRAGConfig
from core.code_exceptions import GraphRAGError


@dataclass
class ServiceRegistration:
    """Service registration metadata."""
    interface: Type
    implementation: Type
    factory: Optional[Callable] = None
    singleton: bool = True
    instance: Optional[Any] = None


class DIContainer(ServiceContainer):
    """Dependency injection container implementation."""
    
    def __init__(self) -> None:
        """Initialize the container."""
        self._services: Dict[Type, ServiceRegistration] = {}
        self._config: Optional[GraphRAGConfig] = None
    
    def register(
        self, 
        interface: Type, 
        implementation: Type,
        factory: Optional[Callable] = None,
        singleton: bool = True
    ) -> None:
        """Register a service implementation.
        
        Args:
            interface: Service interface class.
            implementation: Service implementation class.
            factory: Optional factory function for creating instances.
            singleton: Whether to create singleton instances.
        """
        self._services[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            factory=factory,
            singleton=singleton
        )
    
    def get(self, interface: Type) -> Any:
        """Get a service instance.
        
        Args:
            interface: Service interface class.
            
        Returns:
            Service instance.
            
        Raises:
            GraphRAGError: If service is not registered.
        """
        if interface not in self._services:
            raise GraphRAGError(f"Service {interface.__name__} not registered")
        
        registration = self._services[interface]
        
        # Return singleton instance if exists
        if registration.singleton and registration.instance is not None:
            return registration.instance
        
        # Create new instance
        if registration.factory:
            instance = registration.factory()
        else:
            instance = self._create_instance(registration.implementation)
        
        # Cache singleton
        if registration.singleton:
            registration.instance = instance
        
        return instance
    
    def configure(self, config: GraphRAGConfig) -> None:
        """Configure services with settings.
        
        Args:
            config: Configuration object.
        """
        self._config = config
        
        # Configure existing singleton instances
        for registration in self._services.values():
            if registration.instance and hasattr(registration.instance, 'configure'):
                registration.instance.configure(config)
    
    def _create_instance(self, implementation: Type) -> Any:
        """Create instance with dependency injection.
        
        Args:
            implementation: Class to instantiate.
            
        Returns:
            Created instance.
        """
        # Simple constructor injection
        try:
            # Try to get config if constructor expects it
            import inspect
            sig = inspect.signature(implementation.__init__)
            
            if 'config' in sig.parameters and self._config:
                return implementation(config=self._config)
            else:
                return implementation()
        except Exception as exc:
            raise GraphRAGError(f"Failed to create instance of {implementation.__name__}: {exc}") from exc
    
    def register_defaults(self) -> None:
        """Register default service implementations."""
        # This will be populated after we create the concrete implementations
        pass
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._config = None
    
    def has(self, interface: Type) -> bool:
        """Check if service is registered.
        
        Args:
            interface: Service interface class.
            
        Returns:
            True if registered, False otherwise.
        """
        return interface in self._services


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global dependency injection container.
    
    Returns:
        Global container instance.
    """
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def configure_services(config: GraphRAGConfig) -> DIContainer:
    """Configure services with given configuration.
    
    Args:
        config: Configuration object.
        
    Returns:
        Configured container.
    """
    container = get_container()
    container.configure(config)
    return container


# Decorator for dependency injection
def inject(interface: Type):
    """Decorator for automatic dependency injection.
    
    Args:
        interface: Service interface to inject.
        
    Returns:
        Decorated function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.get(interface)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator
