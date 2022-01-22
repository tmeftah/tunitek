from os import name
from flask import Flask, render_template, abort, request, redirect, url_for, jsonify
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.engine import base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy.orm import sessionmaker


engine = create_engine(
    "sqlite:///database.sqlite", echo=True, connect_args={"check_same_thread": False}
)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

Session = sessionmaker(bind=engine)
session = Session()


def paginate(query, page_number, page_limit):
    length = query.count()
    page_number = page_number - 1

    if page_number > 0:
        query = query.offset((page_number) * page_limit)
    query = query.limit(page_limit)
    return query, length


class Products(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    related_products = relationship("RelatedProducts", back_populates="product")

    def __repr__(self):
        return "<Products '{}'>".format(self.name)


class Tasks(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    choices = relationship("Choices", back_populates="task")
    related_products = relationship("RelatedProducts", back_populates="task")

    def __repr__(self):
        return "<Tasks '{}'>".format(self.name)


class Choices(Base):
    __tablename__ = "choices"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    task = relationship("Tasks", back_populates="choices")

    def __repr__(self):
        return "<Choices '{}'>".format(self.name)


class RelatedProducts(Base):
    __tablename__ = "related_products"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    task = relationship("Tasks", back_populates="related_products")
    product = relationship("Products", back_populates="related_products")

    def __repr__(self):
        return "<RelatedProducts '{}'>".format(self.id)


class Projects(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    tasktracings = relationship("TaskTracing", back_populates="project")

    def __repr__(self) -> str:
        return "<Projects '{}'>".format(self.id)


class TaskTracing(Base):
    __tablename__ = "task_tracing"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    project = relationship("Projects", back_populates="tasktracings", uselist=False)
    task = relationship("Tasks", uselist=False)

    def __repr__(self) -> str:
        return "<TaskTracing '{}'>".format(self.id)


class ChoiceTracing(Base):
    __tablename__ = "choice_tracing"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    choice_id = Column(Integer, ForeignKey("choices.id"))

    def __repr__(self) -> str:
        return "<ChoiceTracing '{}'>".format(self.id)


Base.metadata.create_all(engine)

app = Flask(
    __name__, static_url_path="", static_folder="web/static", template_folder="web/templates"
)


@app.route("/")
def index():
    tasks = session.query(Tasks).all()
    return render_template("index.html", tasks=tasks)


@app.route("/<int:page>")
def index2(page):
    # tasks = session.query(Tasks).limit(1).all()
    task, lenght = paginate(session.query(Tasks), page, 1)
    if page > lenght or page < 1:
        abort(404)
    if page >= lenght:
        next_page = lenght + 1
    else:
        next_page = page + 1

    if page == 1:
        previous_page = 0
    else:
        previous_page = page - 1

    return render_template(
        "index2.html",
        task=task.first(),
        previous_page=previous_page,
        next_page=next_page,
        lenght=lenght,
        page=page,
    )


@app.route("/", methods=["POST"])
def add_task():
    task_name = request.form["task"]
    description = request.form["description"]
    image = request.files["image"]
    new_task = Tasks(name=task_name, description=description)
    session.add(new_task)
    session.commit()

    return redirect(url_for("index2", page=new_task.id))


@app.route("/add_choice/<int:id>", methods=["POST"])
def add_choice(id):
    choice_name = request.form["choice"]
    new_choice = Choices(name=choice_name, task_id=id)
    session.add(new_choice)
    session.commit()

    return redirect(url_for("index2", page=id))


@app.route("/products", methods=["GET"])
def get_products():
    products = session.query(Products).all()
    return render_template("products.html", products=products)


@app.route("/products/json", methods=["GET"])
def get_products_json():
    task_id = int(request.args.get("task_id")) if request.args.get("task_id") else -1

    print(20 * "*", task_id, 20 * "*")
    if task_id > 0:
        related_products = (
            session.query(RelatedProducts).filter(RelatedProducts.task_id == task_id).all()
        )
        ids = [related_product.product_id for related_product in related_products]
        products = session.query(Products).filter(Products.id.notin_(ids)).all()

    else:
        products = session.query(Products).all()

    res = []
    for product in products:
        res.append({"id": product.id, "name": product.name, "description": product.description})

    return jsonify(res)


@app.route("/products", methods=["POST"])
def add_product():
    product_name = request.form["name"]
    description = request.form["description"]
    new_product = Products(name=product_name, description=description)
    session.add(new_product)
    session.commit()
    return redirect(url_for("get_products"))


@app.route("/add_related_product/<int:id>", methods=["POST"])
def add_related_product(id):
    product_id = request.form["product_id"]
    new_related_product = RelatedProducts(task_id=id, product_id=product_id)
    session.add(new_related_product)
    session.commit()

    return redirect(url_for("index2", page=id))


@app.route("/projects", methods=["GET"])
def get_projects():
    projects = session.query(Projects).all()
    return render_template("projects.html", projects=projects)


@app.route("/projects", methods=["POST"])
def add_project():
    project_name = request.form["name"]
    description = request.form["description"]
    new_project = Projects(name=project_name, description=description)
    session.add(new_project)
    session.commit()
    return redirect(url_for("get_project"))


@app.route("/projects/<int:id>", methods=["GET"])
def get_project(id):

    project = session.query(Projects).filter(Projects.id == id).first()

    return render_template("project.html", project=project)


@app.route("/tasks/json", methods=["GET"])
def get_tasks_json():
    project_id = int(request.args.get("project_id")) if request.args.get("project_id") else -1

    print(20 * "*", project_id, 20 * "*")
    if project_id > 0:
        task_tracings = (
            session.query(TaskTracing).filter(TaskTracing.project_id == project_id).all()
        )

        ids = [task_tracing.task_id for task_tracing in task_tracings]

        tasks = session.query(Tasks).filter(Tasks.id.notin_(ids)).all()

    else:
        tasks = session.query(Tasks).all()

    res = []
    for task in tasks:
        res.append({"id": task.id, "name": task.name, "description": task.description})

    return jsonify(res)


@app.route("/tasktracing/<int:project_id>", methods=["POST"])
def add_task_to_project(project_id):

    task_id = request.form["task_id"]
    new_tasktracing = TaskTracing(project_id=project_id, task_id=task_id)

    session.add(new_tasktracing)
    session.commit()
    return redirect(url_for("get_project", id=project_id))


@app.route("/project/<int:project_id>/task/<int:task_id>", methods=["GET"])
def get_task_of_project(project_id, task_id):

    tasktracing = (
        session.query(TaskTracing)
        .filter(TaskTracing.project_id == project_id, TaskTracing.task_id == task_id)
        .first()
    )
    if not tasktracing:
        abort(404)

    return render_template(
        "tasktracing.html",
        tasktracing=tasktracing,
        previous_page=0,
        next_page=2,
        lenght=1,
        page=1,
    )


if __name__ == "__main__":
    app.run(port=3000, debug=True)
