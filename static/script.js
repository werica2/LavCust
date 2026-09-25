function abrirMenu() {

    const menu =
        document.getElementById("menuLateral");

    const overlay =
        document.getElementById("menuOverlay");


    if (menu) {
        menu.classList.add("aberto");
    }


    if (overlay) {
        overlay.classList.add("ativo");
    }


    document.body.classList.add("menu-aberto");
}


function fecharMenu() {

    const menu =
        document.getElementById("menuLateral");

    const overlay =
        document.getElementById("menuOverlay");


    if (menu) {
        menu.classList.remove("aberto");
    }


    if (overlay) {
        overlay.classList.remove("ativo");
    }


    document.body.classList.remove("menu-aberto");
}


document.addEventListener(
    "DOMContentLoaded",
    function () {

        const dataAtual =
            document.getElementById("dataAtual");


        if (dataAtual) {

            const hoje = new Date();


            const texto =
                hoje.toLocaleDateString(
                    "pt-BR",
                    {
                        day: "2-digit",
                        month: "long",
                        year: "numeric"
                    }
                );


            dataAtual.textContent = texto;

        }


        document.addEventListener(
            "keydown",
            function (evento) {

                if (evento.key === "Escape") {
                    fecharMenu();
                }

            }
        );

    }
);