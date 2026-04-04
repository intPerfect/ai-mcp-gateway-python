# -*- coding: utf-8 -*-
"""
MCP Gateway Router - SSE endpoints for MCP protocol
"""
import json
import asyncio
import logging
from fastapi import APIRouter, Query, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.domain.session import session_manager, MessageHandler
from app.domain.auth import AuthService, LicenseCommand
from app.utils.exceptions import AppException, AuthException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{gateway_id}/mcp/sse")
async def handle_sse_connection(
    gateway_id: str,
    api_key: str = Query(default="", alias="api_key"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle SSE connection for MCP protocol
    
    This endpoint establishes a Server-Sent Events connection and returns
    the message endpoint URL for the client to send messages.
    
    Args:
        gateway_id: Gateway identifier
        api_key: API key for authentication
        
    Returns:
        SSE event stream
    """
    try:
        logger.info(f"Establishing MCP SSE connection, gateway_id: {gateway_id}")
        
        if not gateway_id:
            raise AppException("ILLEGAL_PARAMETER", "gateway_id is required")
        
        # Validate authentication
        auth_service = AuthService(db)
        try:
            await auth_service.validate_license(LicenseCommand(gateway_id=gateway_id, api_key=api_key))
        except AuthException as e:
            logger.warning(f"Auth failed for gateway {gateway_id}: {e.message}")
            # Return error event
            err_code, err_msg = e.code, e.message
            async def error_generator():
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "code": err_code,
                        "info": err_msg
                    })
                }
            return EventSourceResponse(error_generator())
        
        # Create session
        session = await session_manager.create_session(gateway_id, api_key)
        
        # Build message endpoint
        message_endpoint = f"/api-gateway/{gateway_id}/mcp/sse?sessionId={session.session_id}"
        if api_key:
            message_endpoint += f"&api_key={api_key}"
        
        async def event_generator():
            """Generate SSE events"""
            try:
                # Send endpoint event
                yield {
                    "event": "endpoint",
                    "data": message_endpoint
                }
                
                # Keep connection alive and forward messages
                while session.is_active:
                    try:
                        # Wait for messages with timeout for heartbeat
                        message = await asyncio.wait_for(
                            session.message_queue.get(),
                            timeout=30.0
                        )
                        
                        if message is None:
                            # Session closed
                            break
                        
                        # Forward message to client
                        yield {
                            "event": "message",
                            "data": json.dumps(message) if isinstance(message, dict) else message
                        }
                        
                    except asyncio.TimeoutError:
                        # Send heartbeat/ping
                        yield {
                            "event": "ping",
                            "data": ""
                        }
                        
            except asyncio.CancelledError:
                logger.info(f"SSE connection cancelled for session {session.session_id}")
            except Exception as e:
                logger.error(f"Error in SSE event generator: {e}")
            finally:
                # Cleanup session
                await session_manager.remove_session(session.session_id)
        
        return EventSourceResponse(event_generator())
        
    except AppException as e:
        logger.error(f"SSE connection rejected, gateway_id: {gateway_id}, error: {e.message}")
        err_code, err_msg = e.code, e.message
        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "code": err_code,
                    "info": err_msg
                })
            }
        return EventSourceResponse(error_generator())
    except Exception as e:
        logger.error(f"SSE connection failed, gateway_id: {gateway_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{gateway_id}/mcp/sse")
async def handle_message(
    gateway_id: str,
    request: Request,
    sessionId: str = Query(..., alias="sessionId"),
    api_key: str = Query(default="", alias="api_key"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handle MCP message
    
    This endpoint receives JSON-RPC messages from the client,
    processes them, and sends responses through the SSE connection.
    
    Args:
        gateway_id: Gateway identifier
        sessionId: Session identifier
        api_key: API key for authentication
        request: HTTP request containing JSON-RPC message
        
    Returns:
        HTTP 202 Accepted
    """
    try:
        message_body = await request.body()
        message_body = message_body.decode("utf-8")
        
        logger.info(f"Processing MCP message, gateway_id: {gateway_id}, sessionId: {sessionId}, message: {message_body[:200]}...")
        
        if not gateway_id or not sessionId:
            raise AppException("ILLEGAL_PARAMETER", "gateway_id and sessionId are required")
        
        # Get session
        session = await session_manager.get_session(sessionId)
        if not session:
            raise AppException("SESSION_NOT_FOUND", f"Session not found: {sessionId}")
        
        # Handle message
        handler = MessageHandler(db)
        response = await handler.handle(gateway_id, message_body)
        
        # Put response in session queue
        await session.message_queue.put(response)
        
        return Response(status_code=202)
        
    except AppException as e:
        logger.error(f"Message handling failed: {e.message}")
        return JSONResponse(
            status_code=400,
            content={"code": e.code, "info": e.message}
        )
    except Exception as e:
        logger.error("Message handling error", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "info": str(e)}
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-gateway"}
