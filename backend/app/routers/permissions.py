from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.permissions import check_permission

router = APIRouter(prefix="/api/permissions", tags=["permissions"])

@router.get("", response_model=list[schemas.PermissionRuleOut])
def list_permissions(acting_user: str, db: Session = Depends(get_db)):
    if not check_permission(db, acting_user, "權限維護", "read"):
        raise HTTPException(403, "沒有權限查看")
    return db.query(models.PermissionRule).all()

@router.post("", response_model=schemas.PermissionRuleOut)
def create_permission(payload: schemas.PermissionRuleCreateIn, acting_user: str, db: Session = Depends(get_db)):
    if not check_permission(db, acting_user, "權限維護", "create"):
        raise HTTPException(403, "沒有權限新增")
    rule = models.PermissionRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.put("/{rule_id}", response_model=schemas.PermissionRuleOut)
def update_permission(rule_id: int, payload: schemas.PermissionRuleUpdateIn, acting_user: str, db: Session = Depends(get_db)):
    if not check_permission(db, acting_user, "權限維護", "update"):
        raise HTTPException(403, "沒有權限修改")
    rule = db.query(models.PermissionRule).filter(models.PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.can_create = payload.can_create
    rule.can_read = payload.can_read
    rule.can_update = payload.can_update
    rule.can_delete = payload.can_delete
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/{rule_id}", status_code=204)
def delete_permission(rule_id: int, acting_user: str, db: Session = Depends(get_db)):
    if not check_permission(db, acting_user, "權限維護", "delete"):
        raise HTTPException(403, "沒有權限刪除")
    rule = db.query(models.PermissionRule).filter(models.PermissionRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    if rule.role in ("admin", "owner", "other"):
        raise HTTPException(400, "不可刪除系統預設角色")
    db.delete(rule)
    db.commit()
    return None
