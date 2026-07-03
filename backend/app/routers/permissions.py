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

@router.get("/me", response_model=dict[str, dict[str, dict[str, bool]]])
def get_my_permissions(acting_user: str, db: Session = Depends(get_db)):
    modules = ["歷史訂單", "建立餐廳", "權限維護", "編輯餐廳資料", "開單與投票", "訂單", "投票"]
    result = {}
    for mod in modules:
        global_perms = {
            "create": check_permission(db, acting_user, mod, "create"),
            "read": check_permission(db, acting_user, mod, "read"),
            "update": check_permission(db, acting_user, mod, "update"),
            "delete": check_permission(db, acting_user, mod, "delete"),
        }
        owned_perms = {
            "create": check_permission(db, acting_user, mod, "create", acting_user),
            "read": check_permission(db, acting_user, mod, "read", acting_user),
            "update": check_permission(db, acting_user, mod, "update", acting_user),
            "delete": check_permission(db, acting_user, mod, "delete", acting_user),
        }
        result[mod] = {"global": global_perms, "owned": owned_perms}
    return result

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
