from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
import xmlrpc.client
from fastapi.openapi.utils import get_openapi

app = FastAPI()

# Odoo connection parameters
url = 'http://127.0.0.1:8069'
db = 'odoo_bmit'
username = 'sakib@bmitodoo.com'
password = 'admin'

# Initialize Odoo XML-RPC client
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    raise HTTPException(status_code=500, detail="Unable to authenticate with Odoo")

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def fetch_odoo_data():
    partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
                                 [[['is_company', '=', True]]],
                                 {'fields': ['id', 'name', 'email', 'phone']})
    return partners

def fetch_partner_by_id(partner_id):
    partner = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
                                [[['id', '=', partner_id]]],
                                {'fields': ['id', 'name', 'email', 'phone'], 'limit': 1})
    if partner:
        return partner[0]
    else:
        return None

def create_partner(name, email, phone):
    partner_id = models.execute_kw(db, uid, password, 'res.partner', 'create',
                                    [{'name': name, 'email': email, 'phone': phone}])
    return partner_id

def update_partner(partner_id, name=None, email=None, phone=None):
    vals = {}
    if name:
        vals['name'] = name
    if email:
        vals['email'] = email
    if phone:
        vals['phone'] = phone
    
    models.execute_kw(db, uid, password, 'res.partner', 'write', [[partner_id], vals])

def delete_partner(partner_id):
    models.execute_kw(db, uid, password, 'res.partner', 'unlink', [[partner_id]])

@app.get("/", response_class=HTMLResponse)
async def read_odoo_data(request: Request):
    odoo_data = fetch_odoo_data()
    template_env = Environment(loader=FileSystemLoader("templates"))
    template = template_env.get_template("odoo_data.html")
    rendered_html = template.render(odoo_data=odoo_data)
    return HTMLResponse(content=rendered_html)

@app.get("/partners", response_class=JSONResponse)
async def read_odoo_data_json():
    odoo_data = fetch_odoo_data()
    return JSONResponse(content=odoo_data)

@app.get("/partners/{partner_id}", response_class=JSONResponse)
async def get_partner_by_id(partner_id: int):
    partner = fetch_partner_by_id(partner_id)
    if partner:
        return JSONResponse(content=partner)
    else:
        raise HTTPException(status_code=404, detail="Partner not found")

class Partner(BaseModel):
    name: str
    email: str
    phone: str

@app.post("/partners", response_class=JSONResponse)
async def create_partner_endpoint(partner: Partner):
    partner_id = create_partner(partner.name, partner.email, partner.phone)
    return {"message": "Partner created", "partner_id": partner_id}

@app.put("/partners/{partner_id}", response_class=JSONResponse)
async def update_partner_endpoint(partner_id: int, partner: Partner):
    update_partner(partner_id, partner.name, partner.email, partner.phone)
    return {"message": "Partner updated"}

@app.delete("/partners/{partner_id}", response_class=JSONResponse)
async def delete_partner_endpoint(partner_id: int):
    delete_partner(partner_id)
    return {"message": "Partner deleted"}

# Add documentation routes
@app.get("/docs", response_class=HTMLResponse)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

@app.get("/openapi.json")
async def get_open_api_endpoint():
    return JSONResponse(get_openapi(title="Your API", version="1.0", routes=app.routes))

