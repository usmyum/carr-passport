from fastapi import APIRouter, Depends, status

from app.modules.ownerships.dependencies import get_ownership_service
from app.modules.ownerships.schemas import (
    OwnershipTransferCreate,
    OwnershipTransferResponse,
)
from app.modules.ownerships.service import OwnershipService
from app.modules.users.dependencies import CurrentUser

router = APIRouter(
    prefix="/transfers",
    tags=["Ownership Transfers"],
)


@router.post(
    "/vehicle/{vehicle_id}",
    response_model=OwnershipTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Offer your vehicle (and its history) to a buyer",
)
async def start_transfer(
    vehicle_id: int,
    data: OwnershipTransferCreate,
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.start_transfer(vehicle_id, data, user=current_user)


@router.get(
    "/incoming",
    response_model=list[OwnershipTransferResponse],
    summary="Transfers waiting for you to accept",
)
async def get_incoming_transfers(
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.list_incoming(user=current_user)


@router.get(
    "/outgoing",
    response_model=list[OwnershipTransferResponse],
    summary="Transfers you have started",
)
async def get_outgoing_transfers(
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.list_outgoing(user=current_user)


@router.post(
    "/{transfer_id}/accept",
    response_model=OwnershipTransferResponse,
    summary="Accept a transfer and become the vehicle's owner",
)
async def accept_transfer(
    transfer_id: int,
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.accept(transfer_id, user=current_user)


@router.post(
    "/{transfer_id}/decline",
    response_model=OwnershipTransferResponse,
    summary="Decline a transfer offered to you",
)
async def decline_transfer(
    transfer_id: int,
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.decline(transfer_id, user=current_user)


@router.post(
    "/{transfer_id}/cancel",
    response_model=OwnershipTransferResponse,
    summary="Cancel a transfer you started",
)
async def cancel_transfer(
    transfer_id: int,
    current_user: CurrentUser,
    service: OwnershipService = Depends(get_ownership_service),
):
    return await service.cancel(transfer_id, user=current_user)
