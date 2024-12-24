from routes import api_routes, llm_routes


def register_routes(app):
    app.include_router(
        router=llm_routes.router,
        prefix='/llm',
        responses={404: {'description': 'Not found'}},
    )

    app.include_router(
        router=api_routes.router,
        prefix='/llm',
        responses={404: {'description': 'Not found'}},
    )

